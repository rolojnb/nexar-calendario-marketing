from __future__ import annotations

import re
from dataclasses import dataclass, field

from services.marketing_models import GeneratedContent, MarketingBrief


EDITORIAL_PATTERNS = (
    "mostra",
    "mostrá",
    "prepara",
    "prepará",
    "podes mencionar",
    "podés mencionar",
    "usa un tono",
    "usá un tono",
    "agrupa el contenido",
    "agrupá el contenido",
    "propuesta de valor:",
    "enfoca el mensaje",
    "enfocá el mensaje",
    "escribir una publicacion",
    "escribir una publicación",
    "crear una publicacion",
    "crear una publicación",
    "disenar una publicacion",
    "diseñar una publicación",
    "disena una publicacion",
    "diseñá una publicación",
)

UNSUPPORTED_CLAIMS = (
    "descuento",
    "oferta",
    "stock limitado",
    "ultimas unidades",
    "últimas unidades",
    "testimonio",
    "garantizado",
    "resultado asegurado",
)


@dataclass(slots=True)
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)


def normalize_hashtags(hashtags: tuple[str, ...] | list[str] | str) -> tuple[str, ...]:
    if isinstance(hashtags, str):
        raw_items = re.split(r"[\s,;]+", hashtags)
    else:
        raw_items = list(hashtags)

    normalized: list[str] = []
    seen: set[str] = set()
    for raw_item in raw_items:
        cleaned = re.sub(r"[^0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", "", str(raw_item or "")).strip()
        if not cleaned:
            continue
        tag = f"#{cleaned.lower()}"
        if tag in seen:
            continue
        seen.add(tag)
        normalized.append(tag)
    return tuple(normalized[:8])


def _plain(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def _contains_editorial_instruction(text: str) -> bool:
    plain = _plain(text)
    return any(pattern in plain for pattern in EDITORIAL_PATTERNS)


def _uses_unsupported_claim(text: str, allowed_facts: tuple[str, ...]) -> bool:
    plain = _plain(text)
    allowed = _plain(" ".join(allowed_facts))
    for claim in UNSUPPORTED_CLAIMS:
        if claim in plain and claim not in allowed:
            return True
    return False


def validate_generated_content(
    content: GeneratedContent,
    brief: MarketingBrief,
) -> ValidationResult:
    errors: list[str] = []
    fields = {
        "title": content.title,
        "caption": content.caption,
        "cta": content.cta,
        "visual_headline": content.visual_headline,
        "visual_subtitle": content.visual_subtitle,
        "visual_cta": content.visual_cta,
    }

    for field_name, value in fields.items():
        if not str(value or "").strip():
            errors.append(f"{field_name} es obligatorio")

    public_text = " ".join([*fields.values(), content.hashtags_text()])
    if _contains_editorial_instruction(public_text):
        errors.append("El contenido contiene instrucciones editoriales internas")
    if _uses_unsupported_claim(public_text, brief.allowed_facts):
        errors.append("El contenido contiene datos no respaldados")

    hashtags = normalize_hashtags(content.hashtags)
    if not hashtags:
        errors.append("Debe incluir al menos un hashtag")
    if hashtags != content.hashtags:
        errors.append("Los hashtags no estan normalizados")

    if len(content.title) > 90:
        errors.append("El titulo es demasiado largo")
    if not (40 <= len(content.caption) <= 700):
        errors.append("El caption debe tener una longitud razonable")
    if len(content.cta) > 120:
        errors.append("El CTA es demasiado largo")
    if len(content.visual_headline) > 42:
        errors.append("El titulo visual es demasiado largo")
    if len(content.visual_subtitle) > 80:
        errors.append("El subtitulo visual es demasiado largo")
    if len(content.visual_cta) > 34:
        errors.append("El CTA visual es demasiado largo")
    if content.caption.strip() in {
        content.visual_headline.strip(),
        content.visual_subtitle.strip(),
    }:
        errors.append("El texto visual no debe duplicar el caption completo")

    return ValidationResult(valid=not errors, errors=errors)
