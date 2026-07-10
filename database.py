from __future__ import annotations

import sqlite3
from pathlib import Path


def get_connection(db_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with get_connection(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS marketing_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                canal TEXT NOT NULL,
                tipo TEXT NOT NULL,
                titulo TEXT NOT NULL,
                texto TEXT NOT NULL,
                hashtags TEXT DEFAULT '',
                cta TEXT DEFAULT '',
                imagen_path TEXT DEFAULT '',
                producto_nombre TEXT DEFAULT '',
                producto_id TEXT DEFAULT '',
                categoria_nombre TEXT DEFAULT '',
                imagen_producto_path TEXT DEFAULT '',
                origen_contenido TEXT DEFAULT 'generico',
                fecha_especial_nombre TEXT DEFAULT '',
                prioridad TEXT DEFAULT '',
                estado TEXT DEFAULT 'borrador',
                created_at TEXT NOT NULL
            )
            """
        )
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(marketing_posts)").fetchall()
        }
        if "fecha_especial_nombre" not in columns:
            connection.execute(
                "ALTER TABLE marketing_posts ADD COLUMN fecha_especial_nombre TEXT DEFAULT ''"
            )
        if "prioridad" not in columns:
            connection.execute(
                "ALTER TABLE marketing_posts ADD COLUMN prioridad TEXT DEFAULT ''"
            )
        if "cta" not in columns:
            connection.execute(
                "ALTER TABLE marketing_posts ADD COLUMN cta TEXT DEFAULT ''"
            )
        if "producto_nombre" not in columns:
            connection.execute(
                "ALTER TABLE marketing_posts ADD COLUMN producto_nombre TEXT DEFAULT ''"
            )
        if "producto_id" not in columns:
            connection.execute(
                "ALTER TABLE marketing_posts ADD COLUMN producto_id TEXT DEFAULT ''"
            )
        if "categoria_nombre" not in columns:
            connection.execute(
                "ALTER TABLE marketing_posts ADD COLUMN categoria_nombre TEXT DEFAULT ''"
            )
        if "imagen_producto_path" not in columns:
            connection.execute(
                "ALTER TABLE marketing_posts ADD COLUMN imagen_producto_path TEXT DEFAULT ''"
            )
        if "origen_contenido" not in columns:
            connection.execute(
                "ALTER TABLE marketing_posts ADD COLUMN origen_contenido TEXT DEFAULT 'generico'"
            )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS business_profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                nombre_comercial TEXT NOT NULL DEFAULT '',
                rubro TEXT NOT NULL DEFAULT '',
                descripcion TEXT NOT NULL DEFAULT '',
                publico_objetivo TEXT NOT NULL DEFAULT '',
                ciudad_zona TEXT NOT NULL DEFAULT '',
                propuesta_valor TEXT NOT NULL DEFAULT '',
                productos_servicios_principales TEXT NOT NULL DEFAULT '',
                objetivo_comercial TEXT NOT NULL DEFAULT '',
                tono_comunicacion TEXT NOT NULL DEFAULT 'cercano y profesional',
                instagram TEXT NOT NULL DEFAULT '',
                whatsapp TEXT NOT NULL DEFAULT '',
                sitio_web TEXT NOT NULL DEFAULT '',
                colores_marca TEXT NOT NULL DEFAULT '',
                logo_path TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS catalog_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                descripcion TEXT NOT NULL DEFAULT '',
                categoria TEXT NOT NULL DEFAULT '',
                precio REAL,
                stock REAL,
                item_type TEXT NOT NULL DEFAULT 'producto',
                featured INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                image_path TEXT NOT NULL DEFAULT '',
                deleted_at TEXT DEFAULT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.commit()
