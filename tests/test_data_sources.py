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


if __name__ == "__main__":
    unittest.main()
