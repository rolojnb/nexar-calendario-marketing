from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from database import init_db
from services.calendario import generate_month_content
from services.data_sources import BusinessDataContext, ProductData, load_business_context
from services.data_sources.nexar_comercio import normalize_product
from services.generador_posts import generate_month_posts
from services.manual_store import create_catalog_item, upsert_business_profile


BRAND_SETTINGS = {
    "name": "Marca Test",
    "primary": "#1D4ED8",
    "secondary": "#0F172A",
    "accent": "#F59E0B",
    "font_family": "DejaVuSans",
    "instagram": "@marca",
    "url": "www.marca.test",
    "logo_path": "",
    "backgrounds_dir": "",
}


class DataSourceTests(unittest.TestCase):
    def test_empty_context_without_external_database(self) -> None:
        context = load_business_context(
            source="nexar_comercio",
            nexar_comercio_db_path="/tmp/no-existe-nexar.sqlite",
        )

        self.assertFalse(context.available)
        self.assertEqual(context.source, "nexar_comercio")
        self.assertEqual(context.to_legacy_dict()["productos"], [])

    def test_normalize_product(self) -> None:
        product = normalize_product(
            {
                "producto_id": 42,
                "producto_nombre": "Yerba",
                "categoria_nombre": "Almacen",
                "precio_valor": "1200.5",
                "stock_valor": "8",
                "imagen_producto_path": "/tmp/yerba.png",
                "total_vendido": "3",
            }
        )

        self.assertEqual(product.producto_id, "42")
        self.assertEqual(product.nombre, "Yerba")
        self.assertEqual(product.categoria, "Almacen")
        self.assertEqual(product.precio, 1200.5)
        self.assertEqual(product.stock, 8.0)
        self.assertEqual(product.ventas, 3.0)

    def test_manual_source_loads_profile_and_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "calendario.db")
            init_db(db_path)
            upsert_business_profile(
                db_path,
                {
                    "nombre_comercial": "Cafe Central",
                    "rubro": "Cafeteria",
                    "descripcion": "Cafe de especialidad.",
                    "publico_objetivo": "Personas que trabajan remoto",
                    "objetivo_comercial": "Vender combos de desayuno",
                    "ciudad_zona": "San Juan",
                    "propuesta_valor": "Atencion rapida",
                    "productos_servicios_principales": "Cafe, brunch",
                    "tono_comunicacion": "calido",
                    "instagram": "cafecentral",
                    "whatsapp": "+54 264 123456",
                    "sitio_web": "https://cafecentral.test",
                    "colores_marca": "#112233,#445566,#778899",
                },
            )
            create_catalog_item(
                db_path,
                {
                    "nombre": "Brunch ejecutivo",
                    "descripcion": "Incluye cafe y tostadas.",
                    "categoria": "Combos",
                    "item_type": "servicio",
                    "featured": "1",
                    "active": "1",
                },
            )

            context = load_business_context(source="manual", manual_db_path=db_path)

        self.assertTrue(context.available)
        self.assertEqual(context.source, "manual")
        self.assertEqual(context.business_profile["nombre_comercial"], "Cafe Central")
        self.assertEqual(context.productos[0].nombre, "Brunch ejecutivo")
        self.assertEqual(context.productos[0].tipo, "servicio")
        self.assertEqual(context.to_legacy_dict()["business_profile"]["objetivo_comercial"], "Vender combos de desayuno")

    def test_manual_fallback_is_used_when_external_source_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "calendario.db")
            init_db(db_path)
            upsert_business_profile(
                db_path,
                {
                    "nombre_comercial": "Studio Norte",
                    "rubro": "Diseno",
                    "descripcion": "Branding y piezas visuales.",
                    "publico_objetivo": "Pymes",
                    "objetivo_comercial": "Conseguir reuniones",
                },
            )

            context = load_business_context(
                source="nexar_comercio",
                nexar_comercio_db_path="/tmp/base-inexistente.sqlite",
                manual_db_path=db_path,
            )

        self.assertTrue(context.available)
        self.assertEqual(context.source, "manual")
        self.assertEqual(context.metadata["fallback_from"], "nexar_comercio")

    def test_supported_source_selection(self) -> None:
        context = load_business_context(source="manual")

        self.assertIsInstance(context, BusinessDataContext)
        self.assertEqual(context.source, "manual")
        self.assertFalse(context.available)

    def test_unknown_source_returns_safe_context(self) -> None:
        context = load_business_context(source="woocommerce")

        self.assertFalse(context.available)
        self.assertEqual(context.source, "woocommerce")
        self.assertEqual(context.metadata["error"], "Fuente de datos no soportada")
        self.assertIn("manual", context.metadata["supported_sources"])

    def test_legacy_context_is_compatible_with_current_engine(self) -> None:
        context = BusinessDataContext(
            available=True,
            source="test",
            productos_mas_vendidos=[
                ProductData(
                    producto_id="sku-1",
                    nombre="Cafe",
                    categoria="Almacen",
                    precio=1500,
                    stock=5,
                    ventas=9,
                )
            ],
        )

        posts = generate_month_posts(
            year=2026,
            month=8,
            brand_name="Marca Test",
            external_context=context.to_legacy_dict(),
        )

        self.assertTrue(posts)
        self.assertIn(
            "producto_mas_vendido",
            {post["origen_contenido"] for post in posts},
        )

    def test_month_generation_without_nexar_comercio_configured(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_path = temp_path / "calendario.db"
            generated_dir = temp_path / "generated"
            init_db(str(db_path))

            with patch("services.calendario.generate_post_image", return_value=""):
                generated = generate_month_content(
                    db_path=str(db_path),
                    month_str="2026-08",
                    generated_dir=str(generated_dir),
                    brand_settings=BRAND_SETTINGS,
                    external_db_path="",
                    data_source="nexar_comercio",
                )

        self.assertGreater(generated, 0)

    def test_month_generation_uses_manual_catalog_and_goal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_path = temp_path / "calendario.db"
            generated_dir = temp_path / "generated"
            init_db(str(db_path))
            upsert_business_profile(
                str(db_path),
                {
                    "nombre_comercial": "Optica Sur",
                    "rubro": "Optica",
                    "descripcion": "Lentes y controles.",
                    "publico_objetivo": "Familias",
                    "objetivo_comercial": "Generar consultas por WhatsApp",
                    "propuesta_valor": "Atencion personalizada",
                },
            )
            create_catalog_item(
                str(db_path),
                {
                    "nombre": "Control visual",
                    "descripcion": "Chequeo preventivo.",
                    "categoria": "Servicios",
                    "item_type": "servicio",
                    "featured": "1",
                    "active": "1",
                },
            )

            with patch("services.calendario.generate_post_image", return_value=""):
                generated = generate_month_content(
                    db_path=str(db_path),
                    month_str="2026-08",
                    generated_dir=str(generated_dir),
                    brand_settings={**BRAND_SETTINGS, "name": "Optica Sur"},
                    external_db_path="",
                    data_source="manual",
                )

            context = load_business_context(source="manual", manual_db_path=str(db_path))
            posts = generate_month_posts(
                year=2026,
                month=8,
                brand_name="Optica Sur",
                external_context=context.to_legacy_dict(),
            )

        self.assertGreater(generated, 0)
        self.assertIn("catalogo_manual", {post["origen_contenido"] for post in posts})
        self.assertTrue(
            any(
                "Generar consultas por WhatsApp" in post["texto"] or "Control visual" in post["titulo"]
                for post in posts
            )
        )


if __name__ == "__main__":
    unittest.main()
