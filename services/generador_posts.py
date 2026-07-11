from __future__ import annotations

import calendar
from datetime import date

from services.fechas_especiales import obtener_fecha_especial
from services.data_sources.base import BusinessDataContext, ProductData
from services.marketing_engine import build_marketing_brief, generate_content_from_brief


CHANNEL_ROTATION = (
    "whatsapp_estado",
    "instagram_story",
    "instagram_feed",
)


def _to_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_product(item: dict) -> ProductData:
    return ProductData(
        producto_id=str(item.get("producto_id", "") or ""),
        nombre=str(item.get("producto_nombre", item.get("nombre", "")) or ""),
        descripcion=str(item.get("descripcion", "") or ""),
        categoria=str(item.get("categoria_nombre", item.get("categoria", "")) or ""),
        tipo=str(item.get("tipo", "producto") or "producto"),
        precio=_to_float(item.get("precio_valor")),
        stock=_to_float(item.get("stock_valor")),
        imagen_path=str(item.get("imagen_producto_path", "") or ""),
        ventas=_to_float(item.get("total_vendido")),
        destacado=bool(item.get("destacado", False)),
        activo=bool(item.get("activo", True)),
        raw=dict(item),
    )


def _context_from_legacy(external_context: dict | BusinessDataContext) -> BusinessDataContext:
    if isinstance(external_context, BusinessDataContext):
        return external_context

    def products(key: str) -> list[ProductData]:
        return [_to_product(item) for item in external_context.get(key, [])]

    categories = []
    for category in external_context.get("categorias", []):
        if isinstance(category, dict):
            name = str(category.get("categoria_nombre", "") or category.get("nombre", "") or "").strip()
        else:
            name = str(category or "").strip()
        if name:
            categories.append(name)

    return BusinessDataContext(
        available=bool(external_context.get("available") or external_context.get("business_profile") or external_context.get("productos")),
        source=str(external_context.get("source", "manual") or "manual"),
        business_profile=dict(external_context.get("business_profile") or {}),
        productos=products("productos"),
        productos_destacados=products("productos_destacados"),
        productos_stock_alto=products("productos_stock_alto"),
        productos_bajo_movimiento=products("productos_bajo_movimiento"),
        productos_mas_vendidos=products("productos_mas_vendidos"),
        categorias=categories,
        tables=list(external_context.get("tables") or []),
        ventas_resumen=dict(external_context.get("ventas_resumen") or {}),
        metadata=dict(external_context.get("metadata") or {}),
    )


def generate_month_posts(year: int, month: int, brand_name: str, external_context: dict | BusinessDataContext) -> list[dict]:
    _, last_day = calendar.monthrange(year, month)
    planned_days = [1, 3, 5, 8, 10, 12, 15, 17, 19, 22, 24, 26]
    special_days = []
    for day in range(1, last_day + 1):
        current_date = date(year, month, day)
        if obtener_fecha_especial(current_date):
            special_days.append(day)

    valid_days = sorted({day for day in planned_days if day <= last_day} | set(special_days))

    context = _context_from_legacy(external_context)
    posts: list[dict] = []
    for slot_index, day in enumerate(valid_days):
        current_date = date(year, month, day)
        channel = CHANNEL_ROTATION[slot_index % len(CHANNEL_ROTATION)]
        brief, plan = build_marketing_brief(
            current_date=current_date,
            brand_name=brand_name,
            channel=channel,
            context=context,
            slot_index=slot_index,
        )
        generated = generate_content_from_brief(brief)
        product = plan.product

        posts.append(
            {
                "fecha": current_date.isoformat(),
                "canal": channel,
                "tipo": plan.content_type,
                "titulo": generated.title,
                "texto": generated.public_text(),
                "caption": generated.caption,
                "hashtags": generated.hashtags_text(),
                "cta": generated.cta,
                "visual_headline": generated.visual_headline,
                "visual_subtitle": generated.visual_subtitle,
                "visual_cta": generated.visual_cta,
                "strategy_used": generated.strategy_used,
                "content_provider": generated.provider,
                "content_model": generated.model,
                "generation_status": "generated",
                "producto_nombre": product.nombre if product else "",
                "producto_id": product.producto_id if product else "",
                "categoria_nombre": product.categoria if product else plan.category,
                "imagen_producto_path": product.imagen_path if product else "",
                "origen_contenido": plan.source or "generico",
                "estado": "listo",
                "fecha_especial_nombre": plan.special_date_name,
                "prioridad": plan.priority,
            }
        )

    return posts
