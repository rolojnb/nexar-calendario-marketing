from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config import Config
from database import ensure_runtime_directories, get_connection, init_db
from services.ai.registry import get_content_provider
from services.content_validator import normalize_hashtags, validate_generated_content
from services.data_sources.base import BusinessDataContext, ProductData
from services.generador_imagenes import generate_post_image
from services.generador_posts import generate_month_posts
from services.marketing_engine import (
    MarketingPostPlan,
    build_marketing_brief,
    select_strategy,
)
from services.marketing_models import GeneratedContent, MarketingBrief


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


class PublishReadyContentTests(unittest.TestCase):
    def test_strategy_selection_uses_explicit_objective_rules(self) -> None:
        product = ProductData(nombre="Cafe", stock=3, ventas=10)
        plan = MarketingPostPlan(content_type="producto_destacado", source="manual", product=product)

        self.assertEqual(select_strategy("Resolver un problema de compra", plan, 0), "PAS")
        self.assertEqual(select_strategy("Informar y asesorar clientes", plan, 0), "reciprocidad")
        self.assertEqual(select_strategy("Liquidar stock disponible", plan, 0), "escasez")
        self.assertEqual(select_strategy("Generar confianza con recomendados", plan, 0), "prueba social")

    def test_marketing_brief_is_internal_and_generated_content_is_public(self) -> None:
        context = BusinessDataContext(
            available=True,
            source="manual",
            business_profile={
                "nombre_comercial": "Optica Sur",
                "rubro": "Optica",
                "publico_objetivo": "Familias",
                "objetivo_comercial": "Generar consultas por WhatsApp",
                "propuesta_valor": "Atencion personalizada",
            },
            productos=[ProductData(nombre="Control visual", descripcion="Chequeo preventivo", tipo="servicio")],
        )

        brief, plan = build_marketing_brief(
            current_date=__import__("datetime").date(2026, 8, 3),
            brand_name="Optica Sur",
            channel="instagram_feed",
            context=context,
            slot_index=0,
        )
        post = generate_month_posts(2026, 8, "Optica Sur", context)[0]

        self.assertIsInstance(brief, MarketingBrief)
        self.assertEqual(plan.source, "catalogo_manual")
        self.assertNotIn("allowed_facts", post)
        self.assertNotIn("MarketingBrief", post["texto"])
        self.assertIn("caption", post)
        self.assertIn("visual_headline", post)

    def test_deterministic_provider_generates_final_spanish_content_offline(self) -> None:
        os.environ.pop("OPENAI_API_KEY", None)
        brief = MarketingBrief(
            objective="sumar consultas",
            strategy="AIDA",
            funnel_stage="consideracion",
            channel="instagram_feed",
            content_type="producto_destacado",
            tone="cercano",
            audience="familias",
            product_service_context="Control visual",
            value_proposition="Atencion personalizada",
            allowed_facts=("Control visual", "Atencion personalizada"),
            cta_intent="Escribinos por WhatsApp",
            hashtag_topics=("Optica", "Control visual"),
            visual_direction="simple",
        )

        content = get_content_provider("deterministic").generate_content(brief, {})
        validation = validate_generated_content(
            GeneratedContent(
                title=content.title,
                caption=content.caption,
                cta=content.cta,
                hashtags=normalize_hashtags(content.hashtags),
                visual_headline=content.visual_headline,
                visual_subtitle=content.visual_subtitle,
                visual_cta=content.visual_cta,
                strategy_used=content.strategy_used,
                provider=content.provider,
                model=content.model,
            ),
            brief,
        )

        self.assertTrue(validation.valid, validation.errors)
        self.assertEqual(content.provider, "deterministic")
        self.assertEqual(content.model, "local-rules-v1")
        self.assertIn("Control visual", content.caption)

    def test_validator_rejects_editorial_instructions_and_unsupported_claims(self) -> None:
        brief = MarketingBrief(
            objective="vender",
            strategy="AIDA",
            funnel_stage="descubrimiento",
            channel="instagram_story",
            content_type="promocion",
            tone="cercano",
            audience="clientes",
            product_service_context="Producto",
            value_proposition="Atencion clara",
            allowed_facts=("Producto", "Atencion clara"),
        )
        invalid = GeneratedContent(
            title="Producto",
            caption="Mostra el producto con descuento y stock limitado.",
            cta="Consultanos.",
            hashtags=("#producto",),
            visual_headline="Producto",
            visual_subtitle="Atencion clara",
            visual_cta="Consultanos",
            strategy_used="AIDA",
            provider="deterministic",
            model="local-rules-v1",
        )

        result = validate_generated_content(invalid, brief)

        self.assertFalse(result.valid)
        self.assertGreaterEqual(len(result.errors), 2)

    def test_hashtag_normalization_and_visual_text_are_separate_from_caption(self) -> None:
        self.assertEqual(
            normalize_hashtags("Optica, #Control Visual optica"),
            ("#optica", "#control", "#visual"),
        )
        context = BusinessDataContext(
            available=True,
            source="manual",
            business_profile={"objetivo_comercial": "sumar consultas"},
            productos=[ProductData(nombre="Control visual", descripcion="Chequeo preventivo")],
        )
        post = generate_month_posts(2026, 8, "Optica Sur", context)[0]

        self.assertNotEqual(post["caption"], post["visual_headline"])
        self.assertNotEqual(post["caption"], post["visual_subtitle"])

    def test_runtime_directories_are_centralized_and_created(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = [
                str(Path(temp_dir) / "data"),
                str(Path(temp_dir) / "data" / "uploads"),
                str(Path(temp_dir) / "data" / "exports"),
                str(Path(temp_dir) / "data" / "backups"),
                str(Path(temp_dir) / "data" / "cache"),
            ]
            ensure_runtime_directories(paths)

            for path in paths:
                self.assertTrue(Path(path).is_dir())
        self.assertTrue(str(Config.DATABASE_PATH).endswith("data/calendario.db"))
        self.assertTrue(str(Config.UPLOADS_DIR).endswith("data/uploads"))

    def test_gitignore_excludes_local_databases_uploads_and_exports(self) -> None:
        gitignore = Path(".gitignore").read_text(encoding="utf-8")

        for expected in ("*.db", "*.sqlite", "*.sqlite3", "data/uploads/", "data/exports/", "data/backups/", "*.zip", "*.txt"):
            self.assertIn(expected, gitignore)

    def test_marketing_posts_migration_is_idempotent_and_preserves_legacy_text(self) -> None:
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
                VALUES ('2026-08-01', 'instagram_feed', 'promocion', 'Titulo', 'Copy publico', '#tag', '', 'borrador', '2026-01-01T00:00:00')
                """
            )
            connection.commit()
            connection.close()

            init_db(str(db_path))
            init_db(str(db_path))

            with get_connection(str(db_path)) as migrated:
                row = migrated.execute("SELECT texto, caption FROM marketing_posts WHERE id = 1").fetchone()
                columns = {item["name"] for item in migrated.execute("PRAGMA table_info(marketing_posts)").fetchall()}

        self.assertEqual(row["texto"], "Copy publico")
        self.assertEqual(row["caption"], "Copy publico")
        self.assertIn("visual_headline", columns)
        self.assertIn("generation_status", columns)
        self.assertIn("updated_at", columns)

    def test_image_generation_uses_visual_fields_not_full_caption(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            post = {
                "id": 1,
                "fecha": "2026-08-01",
                "canal": "instagram_feed",
                "tipo": "producto_destacado",
                "titulo": "Titulo publico",
                "texto": "Caption completo que no debe entrar entero en la imagen.",
                "caption": "Caption completo que no debe entrar entero en la imagen.",
                "hashtags": "#test",
                "cta": "Consultanos.",
                "visual_headline": "Titulo visual",
                "visual_subtitle": "Subtitulo breve",
                "visual_cta": "Escribinos",
                "imagen_producto_path": "",
            }
            seen_texts: list[str] = []

            import services.generador_imagenes as image_module

            original_fit_text = image_module._fit_text

            def spy_fit_text(text, *args, **kwargs):
                seen_texts.append(text)
                return original_fit_text(text, *args, **kwargs)

            with patch("services.generador_imagenes._fit_text", side_effect=spy_fit_text):
                image_path = generate_post_image(post, temp_dir, BRAND_SETTINGS)

            generated_files = list(Path(temp_dir).glob("*.png"))

        self.assertTrue(generated_files)
        self.assertTrue(image_path.endswith(".png"))
        self.assertIn("Titulo visual", seen_texts)
        self.assertIn("Subtitulo breve", seen_texts)
        self.assertNotIn("Caption completo que no debe entrar entero en la imagen.", seen_texts)


if __name__ == "__main__":
    unittest.main()
