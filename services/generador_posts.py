from __future__ import annotations

import calendar
from datetime import date

from services.fechas_especiales import obtener_fecha_especial


POST_TYPES = (
    "producto_destacado",
    "tip",
    "promocion",
    "recordatorio",
    "novedad",
)
CHANNEL_ROTATION = (
    "whatsapp_estado",
    "instagram_story",
    "instagram_feed",
)


def _best_product_name(external_context: dict, fallback_index: int) -> str:
    productos = external_context.get("productos") or []
    if not productos:
        return f"Producto {fallback_index + 1}"

    first_product = productos[fallback_index % len(productos)]
    for candidate_key in ("nombre", "titulo", "descripcion", "producto"):
        value = first_product.get(candidate_key)
        if value:
            return str(value)
    return f"Producto {fallback_index + 1}"


def _best_category_name(external_context: dict, fallback_index: int) -> str:
    categorias = external_context.get("categorias") or []
    if not categorias:
        return f"Linea {fallback_index + 1}"

    first_category = categorias[fallback_index % len(categorias)]
    for candidate_key in ("nombre", "titulo", "descripcion", "categoria"):
        value = first_category.get(candidate_key)
        if value:
            return str(value)
    return f"Linea {fallback_index + 1}"


def _build_copy(post_type: str, brand_name: str, external_context: dict, slot_index: int) -> dict:
    product_name = _best_product_name(external_context, slot_index)
    category_name = _best_category_name(external_context, slot_index)

    variants = {
        "promocion": {
            "titulo": f"Promo de {product_name}",
            "texto": (
                f"Esta semana en {brand_name} destacamos {product_name}. "
                "Ideal para mover stock, atraer consultas y reforzar presencia."
            ),
            "hashtags": "#promo #oferta #compralocal",
        },
        "tip": {
            "titulo": f"Tip rapido sobre {category_name}",
            "texto": (
                f"Comparti un consejo simple vinculado a {category_name} para generar valor "
                f"y mantener activa la comunidad de {brand_name}."
            ),
            "hashtags": "#tip #consejo #ventas",
        },
        "producto_destacado": {
            "titulo": f"{product_name} destacado",
            "texto": (
                f"Mostra beneficios, usos y una llamada a la accion directa para que "
                f"{product_name} gane protagonismo en {brand_name}."
            ),
            "hashtags": "#producto #destacado #emprendedores",
        },
        "recordatorio": {
            "titulo": "Recordatorio para tus clientes",
            "texto": (
                "Aprovecha para recordar horarios, medios de pago, envios o promociones vigentes "
                f"de {brand_name}."
            ),
            "hashtags": "#recordatorio #clientes #negocio",
        },
        "novedad": {
            "titulo": f"Novedades en {brand_name}",
            "texto": (
                f"Comunica ingresos recientes, cambios de temporada o una novedad de la linea "
                f"{category_name}."
            ),
            "hashtags": "#novedad #lanzamiento #tienda",
        },
    }
    return variants[post_type]


def _build_special_copy(special_date: dict, brand_name: str) -> dict:
    return {
        "titulo": special_date["sugerencia_titulo"],
        "texto": f"{special_date['sugerencia_texto']} {brand_name} puede aprovechar este momento comercial.",
        "hashtags": special_date["sugerencia_hashtags"],
    }


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
        special_date = obtener_fecha_especial(current_date)
        channel = CHANNEL_ROTATION[slot_index % len(CHANNEL_ROTATION)]

        if special_date:
            copy = _build_special_copy(special_date, brand_name)
            post_type = special_date["tipo"]
        else:
            post_type = POST_TYPES[slot_index % len(POST_TYPES)]
            copy = _build_copy(post_type, brand_name, external_context, slot_index)

        posts.append(
            {
                "fecha": current_date.isoformat(),
                "canal": channel,
                "tipo": post_type,
                "titulo": copy["titulo"],
                "texto": copy["texto"],
                "hashtags": copy["hashtags"],
                "estado": "borrador",
                "fecha_especial_nombre": special_date["nombre"] if special_date else "",
                "prioridad": special_date["prioridad"] if special_date else "",
            }
        )

    # Punto claro para futura integracion de IA generativa sin cambiar el flujo del calendario.
    return posts
