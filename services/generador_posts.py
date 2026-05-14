from __future__ import annotations

import calendar
from datetime import date

from services.fechas_especiales import obtener_fecha_especial
from services.motor_contenido import resolver_publicacion


CHANNEL_ROTATION = (
    "whatsapp_estado",
    "instagram_story",
    "instagram_feed",
)


def generate_month_posts(year: int, month: int, brand_name: str, external_context: dict) -> list[dict]:
    _, last_day = calendar.monthrange(year, month)
    planned_days = [1, 3, 5, 8, 10, 12, 15, 17, 19, 22, 24, 26]
    special_days = []
    for day in range(1, last_day + 1):
        current_date = date(year, month, day)
        if obtener_fecha_especial(current_date):
            special_days.append(day)

    valid_days = sorted({day for day in planned_days if day <= last_day} | set(special_days))

    posts: list[dict] = []
    for slot_index, day in enumerate(valid_days):
        current_date = date(year, month, day)
        channel = CHANNEL_ROTATION[slot_index % len(CHANNEL_ROTATION)]
        resolved = resolver_publicacion(
            current_date=current_date,
            brand_name=brand_name,
            external_context=external_context,
            slot_index=slot_index,
        )

        producto = resolved.get("producto_asociado") or {}
        categoria = resolved.get("categoria_asociada") or {}

        posts.append(
            {
                "fecha": current_date.isoformat(),
                "canal": channel,
                "tipo": resolved["tipo"],
                "titulo": resolved["titulo"],
                "texto": resolved["texto"],
                "hashtags": resolved["hashtags"],
                "cta": resolved.get("cta", ""),
                "producto_nombre": producto.get("producto_nombre", ""),
                "producto_id": producto.get("producto_id", ""),
                "categoria_nombre": categoria.get("categoria_nombre", ""),
                "imagen_producto_path": resolved.get("imagen_producto_path", ""),
                "origen_contenido": resolved.get("origen_contenido", "generico"),
                "estado": "borrador",
                "fecha_especial_nombre": resolved.get("fecha_especial_nombre", ""),
                "prioridad": resolved.get("prioridad", ""),
            }
        )

    return posts
