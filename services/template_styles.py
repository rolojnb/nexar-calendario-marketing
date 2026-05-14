from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TemplateStyle:
    name: str
    eyebrow: str
    accent_mode: str
    overlay_opacity: int
    title_case: str
    cta: str
    icon_text: str
    visual_tone: str


POST_TYPE_STYLES: dict[str, TemplateStyle] = {
    "promocion": TemplateStyle(
        name="promocion",
        eyebrow="PROMO ACTIVA",
        accent_mode="bold",
        overlay_opacity=72,
        title_case="upper",
        cta="Escribinos y pedilo hoy",
        icon_text="OFERTA",
        visual_tone="llamativo",
    ),
    "tip": TemplateStyle(
        name="tip",
        eyebrow="TIP DE LA SEMANA",
        accent_mode="minimal",
        overlay_opacity=42,
        title_case="normal",
        cta="Guardalo para usarlo después",
        icon_text="TIP",
        visual_tone="minimalista",
    ),
    "producto_destacado": TemplateStyle(
        name="producto_destacado",
        eyebrow="DESTACADO",
        accent_mode="spotlight",
        overlay_opacity=58,
        title_case="normal",
        cta="Consultá stock y precio",
        icon_text="TOP",
        visual_tone="enfoque de producto",
    ),
    "novedad": TemplateStyle(
        name="novedad",
        eyebrow="NOVEDAD",
        accent_mode="modern",
        overlay_opacity=54,
        title_case="normal",
        cta="Descubrí lo nuevo de la semana",
        icon_text="NEW",
        visual_tone="moderno",
    ),
    "recordatorio": TemplateStyle(
        name="recordatorio",
        eyebrow="RECORDATORIO",
        accent_mode="clean",
        overlay_opacity=36,
        title_case="normal",
        cta="Agendalo y compartilo con tu cliente",
        icon_text="INFO",
        visual_tone="claro y limpio",
    ),
}


def get_template_style(post_type: str) -> TemplateStyle:
    return POST_TYPE_STYLES.get(post_type, POST_TYPE_STYLES["novedad"])
