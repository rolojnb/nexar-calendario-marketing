from __future__ import annotations

import io
import sqlite3
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from app import create_app
from database import get_connection, init_db
from services.manual_store import (
    create_catalog_item,
    delete_managed_file,
    get_business_profile,
    get_catalog_item,
    get_selected_data_source,
    list_catalog_items,
    parse_brand_colors,
    resolve_managed_path,
    set_selected_data_source,
    soft_delete_catalog_item,
    store_image_upload,
    toggle_catalog_item_active,
    update_catalog_item,
    upsert_business_profile,
)


class ManualStoreTests(unittest.TestCase):
    def test_init_db_migrates_previous_schema_without_losing_posts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "legacy.db"
            connection = sqlite3.connect(db_path)
            connection.execute(
                """
                CREATE TABLE marketing_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TEXT NOT NULL,
                    canal TEXT NOT NULL,
                    tipo TEXT NOT NULL,
                    titulo TEXT NOT NULL,
                    texto TEXT NOT NULL,
                    hashtags TEXT DEFAULT '',
                    imagen_path TEXT DEFAULT '',
                    estado TEXT DEFAULT 'borrador',
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT INTO marketing_posts (fecha, canal, tipo, titulo, texto, hashtags, imagen_path, estado, created_at)
                VALUES ('2026-08-01', 'instagram_feed', 'promocion', 'Titulo', 'Texto', '#tag', '', 'borrador', '2026-01-01T00:00:00')
                """
            )
            connection.commit()
            connection.close()

            init_db(str(db_path))

            with get_connection(str(db_path)) as migrated:
                total_posts = migrated.execute("SELECT COUNT(*) AS total FROM marketing_posts").fetchone()["total"]
                business_exists = migrated.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='business_profile'"
                ).fetchone()
                catalog_exists = migrated.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='catalog_items'"
                ).fetchone()
                columns = {
                    row["name"]
                    for row in migrated.execute("PRAGMA table_info(marketing_posts)").fetchall()
                }

        self.assertEqual(total_posts, 1)
        self.assertIsNotNone(business_exists)
        self.assertIsNotNone(catalog_exists)
        self.assertIn("cta", columns)
        self.assertIn("producto_nombre", columns)
        self.assertIn("origen_contenido", columns)

    def test_business_profile_persists_and_source_selection_is_saved(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_dir = Path(temp_dir) / "data"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "calendario.db")
            init_db(db_path)
            upsert_business_profile(
                db_path,
                {
                    "nombre_comercial": "Panaderia Sol",
                    "rubro": "Panaderia",
                    "descripcion": "Panificados frescos.",
                    "publico_objetivo": "Vecinos del barrio",
                    "objetivo_comercial": "Aumentar pedidos diarios",
                    "instagram": "panaderiasol",
                },
            )
            set_selected_data_source(db_path, "manual")

            profile = get_business_profile(db_path)
            selected_source = get_selected_data_source(db_path)

        self.assertEqual(profile["nombre_comercial"], "Panaderia Sol")
        self.assertEqual(profile["instagram"], "@panaderiasol")
        self.assertEqual(selected_source, "manual")

    def test_catalog_crud_and_soft_delete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_dir = Path(temp_dir) / "data"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "calendario.db")
            init_db(db_path)
            item_id = create_catalog_item(
                db_path,
                {
                    "nombre": "Tarta integral",
                    "descripcion": "Porcion individual.",
                    "categoria": "Comidas",
                    "precio": "2500",
                    "stock": "5",
                    "item_type": "producto",
                    "featured": "1",
                    "active": "1",
                },
            )
            update_catalog_item(
                db_path,
                item_id,
                {
                    "nombre": "Tarta integral premium",
                    "descripcion": "Porcion individual con semillas.",
                    "categoria": "Comidas",
                    "precio": "2800",
                    "stock": "4",
                    "item_type": "producto",
                    "featured": "1",
                    "active": "1",
                },
            )
            is_active = toggle_catalog_item_active(db_path, item_id)
            soft_delete_catalog_item(db_path, item_id)
            listed = list_catalog_items(db_path)
            deleted_item = get_catalog_item(db_path, item_id)

        self.assertFalse(is_active)
        self.assertEqual(listed, [])
        self.assertIsNotNone(deleted_item)
        self.assertIsNotNone(deleted_item["deleted_at"])

    def test_image_storage_uses_managed_paths_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_dir = Path(temp_dir) / "data"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "calendario.db")
            init_db(db_path)
            buffer = io.BytesIO()
            Image.new("RGB", (4, 4), "white").save(buffer, format="PNG")
            buffer.seek(0)

            from werkzeug.datastructures import FileStorage

            stored_path = store_image_upload(
                db_path,
                FileStorage(stream=buffer, filename="../../logo.png", content_type="image/png"),
                bucket="logos",
                prefix="logo",
            )
            resolved = resolve_managed_path(db_path, stored_path)
            unsafe = resolve_managed_path(db_path, "../../etc/passwd")
            delete_managed_file(db_path, stored_path)

        self.assertTrue(stored_path.startswith("data/uploads/logos/logo_"))
        self.assertIsNotNone(resolved)
        self.assertIsNone(unsafe)
        self.assertFalse(resolved.exists())

    def test_create_app_and_manual_routes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "calendario.db"
            generated_dir = Path(temp_dir) / "generated"
            app = create_app()
            app.config.update(
                TESTING=True,
                DATABASE_PATH=str(db_path),
                GENERATED_DIR=str(generated_dir),
            )
            init_db(str(db_path))

            client = app.test_client()
            create_response = client.post(
                "/mi-negocio",
                data={
                    "data_source": "manual",
                    "nombre_comercial": "Clinica Uno",
                    "rubro": "Salud",
                    "descripcion": "Atencion ambulatoria.",
                    "publico_objetivo": "Pacientes particulares",
                    "objetivo_comercial": "Aumentar turnos por WhatsApp",
                },
                follow_redirects=True,
            )
            catalog_response = client.post(
                "/productos-servicios",
                data={
                    "nombre": "Consulta inicial",
                    "descripcion": "Evaluacion general.",
                    "categoria": "Consultas",
                    "item_type": "servicio",
                    "featured": "1",
                    "active": "1",
                },
                follow_redirects=True,
            )
            page_response = client.get("/productos-servicios")
            calendar_response = client.get("/calendario?mes=2026-08")

        self.assertEqual(create_response.status_code, 200)
        self.assertIn("Los datos del negocio se guardaron correctamente".encode(), create_response.data)
        self.assertEqual(catalog_response.status_code, 200)
        self.assertIn("Producto o servicio creado correctamente".encode(), catalog_response.data)
        self.assertEqual(page_response.status_code, 200)
        self.assertEqual(calendar_response.status_code, 200)

    def test_parse_brand_colors_filters_invalid_values(self) -> None:
        colors = parse_brand_colors("#112233, 445566, invalid, #112233")
        self.assertEqual(colors, ["#112233", "#445566"])


if __name__ == "__main__":
    unittest.main()
