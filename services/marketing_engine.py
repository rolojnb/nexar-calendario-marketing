from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from services.ai.registry import get_content_provider
from services.content_validator import normalize_hashtags, validate_generated_content
from services.data_sources.base import BusinessDataContext, ProductData
from services.fechas_especiales import obtener_fecha_especial
from services.marketing_models import GeneratedContent, MarketingBrief


STRATEGIES = (
    "AIDA",
    "PAS",
    "Before-After-Bridge",
    "StoryBrand",
    "storytelling",
    "autoridad",
    "prueba social",
    "reciprocidad",
    "urgencia",
    "escasez",
)


@dataclass(frozen=True, slots=True)
class MarketingPostPlan:
    content_type: str
    source: str
    product: ProductData | None = None
    category: str = ""
    special_date_name: str = ""
    priority: str = ""


def _clean(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _pick(items: list[ProductData], slot_index: int) -> ProductData | None:
    active_items = [item for item in items if item.activo]
    if not active_items:
        return None
    return active_items[slot_index % len(active_items)]


def _profile(context: BusinessDataContext) -> dict[str, Any]:
    return context.business_profile or {}


def _objective(context: BusinessDataContext) -> str:
    return _clean(_profile(context).get("objetivo_comercial"), "sumar consultas")


def _audience(context: BusinessDataContext) -> str:
    return _clean(_profile(context).get("publico_objetivo"), "clientes actuales y potenciales")


def _tone(context: BusinessDataContext) -> str:
    return _clean(_profile(context).get("tono_comunicacion"), "cercano y profesional")


def _value_proposition(context: BusinessDataContext, product: ProductData | None) -> str:
    profile_value = _clean(_profile(context).get("propuesta_valor"))
    if profile_value:
        return profile_value
    if product and product.descripcion:
        return product.descripcion
    return "atencion clara y respuesta por mensaje"


def _product_context(product: ProductData | None, category: str) -> str:
    if product:
        if product.categoria:
            return f"{product.nombre} de {product.categoria}"
        return product.nombre
    if category:
        return f"Opciones de {category}"
    return "Propuesta del negocio"


def _allowed_facts(
    brand_name: str,
    context: BusinessDataContext,
    product: ProductData | None,
    category: str,
    special_date_name: str,
) -> tuple[str, ...]:
    profile = _profile(context)
    facts = [
        brand_name,
        _clean(profile.get("nombre_comercial")),
        _clean(profile.get("rubro")),
        _clean(profile.get("descripcion")),
        _clean(profile.get("publico_objetivo")),
        _clean(profile.get("ciudad_zona")),
        _clean(profile.get("propuesta_valor")),
        _clean(profile.get("productos_servicios_principales")),
        _clean(profile.get("objetivo_comercial")),
        category,
        special_date_name,
    ]
    if product:
        facts.extend(
            [
                product.nombre,
                product.descripcion,
                product.categoria,
                product.tipo,
            ]
        )
        if product.precio is not None:
            facts.append(f"precio {product.precio:g}")
        if product.stock is not None:
            facts.append(f"stock {product.stock:g}")
        if product.ventas is not None:
            facts.append(f"ventas {product.ventas:g}")
    return tuple(fact for fact in facts if fact)


def select_strategy(objective: str, plan: MarketingPostPlan, slot_index: int) -> str:
    text = objective.lower()
    has_stock = bool(plan.product and plan.product.stock is not None)
    has_sales = bool(plan.product and plan.product.ventas is not None)

    if any(word in text for word in ("urgente", "hoy", "rapido", "rapida", "inmediato")):
        return "urgencia"
    if has_stock and any(word in text for word in ("stock", "disponible", "liquidar")):
        return "escasez"
    if has_sales and any(word in text for word in ("confianza", "recomend", "validar")):
        return "prueba social"
    if any(word in text for word in ("educar", "informar", "asesorar", "guia")):
        return "reciprocidad"
    if any(word in text for word in ("posicionar", "experto", "autoridad", "profesional")):
        return "autoridad"
    if any(word in text for word in ("historia", "marca", "comunidad")):
        return "storytelling"
    if any(word in text for word in ("simple", "claridad", "acompanar", "acompañar")):
        return "StoryBrand"
    if any(word in text for word in ("cambio", "mejorar", "transformar")):
        return "Before-After-Bridge"
    if any(word in text for word in ("problema", "resolver", "solucion", "solución")):
        return "PAS"

    rotation = ("AIDA", "PAS", "Before-After-Bridge", "StoryBrand", "storytelling")
    return rotation[slot_index % len(rotation)]


def build_post_plan(context: BusinessDataContext, current_date: date, slot_index: int) -> MarketingPostPlan:
    special = obtener_fecha_especial(current_date)
    if special:
        return MarketingPostPlan(
            content_type=special["tipo"],
            source="fecha_especial",
            special_date_name=special["nombre"],
            priority=special["prioridad"],
        )

    if context.productos_mas_vendidos:
        product = _pick(context.productos_mas_vendidos, slot_index)
        if product:
            return MarketingPostPlan(
                content_type="producto_destacado",
                source="producto_mas_vendido",
                product=product,
            )
    if context.productos_stock_alto:
        product = _pick(context.productos_stock_alto, slot_index)
        if product:
            return MarketingPostPlan(content_type="promocion", source="producto_stock_alto", product=product)
    if context.productos_bajo_movimiento:
        product = _pick(context.productos_bajo_movimiento, slot_index)
        if product:
            return MarketingPostPlan(content_type="recordatorio", source="producto_bajo_movimiento", product=product)

    featured = context.productos_destacados or []
    products = context.productos or []
    category = context.categorias[slot_index % len(context.categorias)] if context.categorias else ""
    product = _pick(featured, slot_index) or _pick(products, slot_index)
    if product:
        content_type = "producto_destacado" if product.tipo == "producto" else "novedad"
        source = "catalogo_manual" if context.source == "manual" else context.source or "catalogo"
        return MarketingPostPlan(content_type=content_type, source=source, product=product)
    if category:
        source = "categoria_manual" if context.source == "manual" else context.source or "categoria"
        return MarketingPostPlan(content_type="novedad", source=source, category=category)
    return MarketingPostPlan(content_type="tip", source="tip_generico")


def build_marketing_brief(
    *,
    current_date: date,
    brand_name: str,
    channel: str,
    context: BusinessDataContext,
    slot_index: int,
) -> tuple[MarketingBrief, MarketingPostPlan]:
    plan = build_post_plan(context, current_date, slot_index)
    objective = _objective(context)
    strategy = select_strategy(objective, plan, slot_index)
    product_context = _product_context(plan.product, plan.category or plan.special_date_name)
    value = _value_proposition(context, plan.product)
    facts = _allowed_facts(
        brand_name,
        context,
        plan.product,
        plan.category,
        plan.special_date_name,
    )
    profile = _profile(context)
    rubro = _clean(profile.get("rubro"), "negocio local")
    cta_intent = "Escribinos para recibir mas informacion"
    if "whatsapp" in objective.lower() or channel == "whatsapp_estado":
        cta_intent = "Escribinos por WhatsApp"
    elif "turno" in objective.lower():
        cta_intent = "Pedinos tu turno"
    elif "venta" in objective.lower() or "pedido" in objective.lower():
        cta_intent = "Consultanos para comprar"

    brief = MarketingBrief(
        objective=objective,
        strategy=strategy,
        funnel_stage="consideracion" if plan.product or plan.category else "descubrimiento",
        channel=channel,
        content_type=plan.content_type,
        tone=_tone(context),
        audience=_audience(context),
        product_service_context=product_context,
        value_proposition=value,
        allowed_facts=facts,
        cta_intent=cta_intent,
        hashtag_topics=(rubro, plan.category, plan.product.categoria if plan.product else "", brand_name),
        visual_direction="pieza clara con jerarquia de titulo, beneficio y CTA",
    )
    return brief, plan


def generate_content_from_brief(brief: MarketingBrief, provider_name: str = "deterministic") -> GeneratedContent:
    provider = get_content_provider(provider_name)
    content = provider.generate_content(brief, settings={})
    normalized = GeneratedContent(
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
    )
    validation = validate_generated_content(normalized, brief)
    if validation.valid:
        return normalized

    fallback_brief = MarketingBrief(
        objective=brief.objective,
        strategy="AIDA",
        funnel_stage=brief.funnel_stage,
        channel=brief.channel,
        content_type=brief.content_type,
        tone="cercano y profesional",
        audience=brief.audience,
        product_service_context=brief.product_service_context,
        value_proposition=brief.value_proposition,
        allowed_facts=brief.allowed_facts,
        cta_intent=brief.cta_intent or "Escribinos para recibir mas informacion",
        hashtag_topics=brief.hashtag_topics,
        visual_direction=brief.visual_direction,
    )
    fallback_content = provider.generate_content(fallback_brief, settings={"fallback": True})
    fallback_normalized = GeneratedContent(
        title=fallback_content.title,
        caption=fallback_content.caption,
        cta=fallback_content.cta,
        hashtags=normalize_hashtags(fallback_content.hashtags),
        visual_headline=fallback_content.visual_headline,
        visual_subtitle=fallback_content.visual_subtitle,
        visual_cta=fallback_content.visual_cta,
        strategy_used=fallback_content.strategy_used,
        provider=fallback_content.provider,
        model=fallback_content.model,
    )
    fallback_validation = validate_generated_content(fallback_normalized, fallback_brief)
    if not fallback_validation.valid:
        raise ValueError("; ".join(fallback_validation.errors))
    return fallback_normalized
