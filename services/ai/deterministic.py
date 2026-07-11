from __future__ import annotations

import re
from typing import Any

from services.ai.base import ContentProvider
from services.marketing_models import GeneratedContent, MarketingBrief


def _sentence(value: str, fallback: str) -> str:
    text = re.sub(r"\s+", " ", value or "").strip(" .")
    return text or fallback


def _short(value: str, limit: int) -> str:
    text = _sentence(value, "")
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].strip(" ,.;:")
    return cut or text[:limit].strip()


def _normalise_hashtag(raw: str) -> str:
    text = re.sub(r"[^0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", "", raw or "").strip()
    if not text:
        return ""
    return f"#{text.lower()}"


class DeterministicContentProvider(ContentProvider):
    provider_name = "deterministic"
    model_name = "local-rules-v1"

    def generate_content(
        self,
        brief: MarketingBrief,
        settings: dict[str, Any] | None = None,
    ) -> GeneratedContent:
        main_fact = _sentence(
            brief.product_service_context or (brief.allowed_facts[0] if brief.allowed_facts else ""),
            "Una propuesta pensada para tu proxima decision de compra",
        )
        audience = _sentence(brief.audience, "personas que buscan una buena opcion")
        value = _sentence(brief.value_proposition, main_fact)
        objective = _sentence(brief.objective, "sumar consultas")
        tone_intro = {
            "cercano": "Con una atencion cercana",
            "calido": "Con una atencion calida",
            "profesional": "Con una propuesta profesional",
            "directo": "De forma simple y directa",
        }
        intro = next(
            (line for key, line in tone_intro.items() if key in brief.tone.lower()),
            "Con una propuesta clara",
        )

        strategy_templates = {
            "AIDA": (
                f"{intro}, {main_fact} ayuda a que {audience} encuentre una alternativa concreta.",
                f"{value}. Es una buena opcion para avanzar con {objective}.",
            ),
            "PAS": (
                f"Cuando {audience} necesita resolver una compra sin vueltas, {main_fact} aporta una respuesta clara.",
                f"{value}. Pedinos informacion y te orientamos con lo disponible.",
            ),
            "Before-After-Bridge": (
                f"Antes de decidir, suele faltar una opcion clara. Con {main_fact}, {audience} puede avanzar con mas seguridad.",
                f"{value}. Te contamos como aprovecharlo segun lo que necesitas.",
            ),
            "StoryBrand": (
                f"{audience.capitalize()} merece una solucion simple. {main_fact} esta pensado para acompanar esa decision.",
                f"{value}. Estamos para ayudarte a elegir el proximo paso.",
            ),
            "storytelling": (
                f"Cada consulta empieza con una necesidad concreta. {main_fact} puede ser el punto de partida para resolverla.",
                f"{value}. Escribinos y lo vemos juntos.",
            ),
            "autoridad": (
                f"{main_fact} reune informacion clara para que {audience} compare y decida mejor.",
                f"{value}. Respondemos tus dudas antes de que avances.",
            ),
            "prueba social": (
                f"{main_fact} se destaca dentro de las opciones que {audience} suele consultar.",
                f"{value}. Consultanos y te pasamos detalles.",
            ),
            "reciprocidad": (
                f"Te acercamos una opcion concreta: {main_fact}.",
                f"{value}. Pedinos ayuda y te compartimos la informacion necesaria.",
            ),
            "urgencia": (
                f"Si estas evaluando opciones ahora, {main_fact} puede ayudarte a decidir sin postergarlo.",
                f"{value}. Escribinos hoy y te respondemos.",
            ),
            "escasez": (
                f"{main_fact} tiene disponibilidad informada para quienes quieren resolver pronto.",
                f"{value}. Consultanos y verificamos la opcion para vos.",
            ),
        }
        first, second = strategy_templates.get(brief.strategy, strategy_templates["AIDA"])
        caption = f"{first}\n\n{second}"
        cta = _sentence(brief.cta_intent, "Escribinos para recibir mas informacion")
        if not cta.endswith((".", "!", "?")):
            cta = f"{cta}."

        hashtags = []
        for topic in (*brief.hashtag_topics, brief.channel, brief.content_type):
            tag = _normalise_hashtag(topic)
            if tag and tag not in hashtags:
                hashtags.append(tag)
        if not hashtags:
            hashtags = ["#negociolocal", "#consultas"]

        title_seed = brief.product_service_context or brief.objective or "Contenido para publicar"
        title = _short(title_seed, 78)
        visual_headline = _short(title_seed, 34)
        visual_subtitle = _short(value, 58)
        visual_cta = _short(brief.cta_intent or "Consultanos", 28)

        return GeneratedContent(
            title=title,
            caption=caption,
            cta=cta,
            hashtags=tuple(hashtags[:5]),
            visual_headline=visual_headline,
            visual_subtitle=visual_subtitle,
            visual_cta=visual_cta,
            strategy_used=brief.strategy,
            provider=self.provider_name,
            model=self.model_name,
        )
