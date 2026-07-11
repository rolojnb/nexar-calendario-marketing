from __future__ import annotations

from datetime import date

from services.fechas_especiales import obtener_fecha_especial


COMMERCIAL_PRIORITIES = (
    "producto_mas_vendido",
    "producto_stock_alto",
    "producto_bajo_movimiento",
    "categoria_destacada",
    "tip_generico",
    "promocion_generica",
)

MANUAL_PRIORITIES = (
    "catalogo_destacado",
    "catalogo_general",
    "categoria_manual",
    "objetivo_manual",
    "tip_generico",
    "promocion_generica",
)


def _format_money(value: object) -> str:
    if value in (None, ""):
        return ""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return str(value)
    if amount.is_integer():
        return f"${int(amount):,}".replace(",", ".")
    return f"${amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _clean_hashtags(*tags: str) -> str:
    seen: set[str] = set()
    ordered: list[str] = []
    for group in tags:
        for raw_tag in group.split():
            tag = raw_tag.strip()
            if not tag or tag in seen:
                continue
            seen.add(tag)
            ordered.append(tag)
    return " ".join(ordered)


def _pick(items: list[dict], slot_index: int) -> dict | None:
    if not items:
        return None
    return items[slot_index % len(items)]


def _business_goal(profile: dict) -> str:
    return str(profile.get("objetivo_comercial") or "sumar consultas y ventas").strip()


def _tone_line(profile: dict) -> str:
    tone = str(profile.get("tono_comunicacion") or "cercano y profesional").strip()
    return tone if tone else "cercano y profesional"


def _build_special_copy(special_date: dict, brand_name: str) -> dict:
    return {
        "tipo": special_date["tipo"],
        "titulo": special_date["sugerencia_titulo"],
        "texto": f"{special_date['sugerencia_texto']} {brand_name} puede aprovechar este momento comercial.",
        "hashtags": special_date["sugerencia_hashtags"],
        "cta": "Aprovecha el momento comercial",
        "producto_asociado": None,
        "categoria_asociada": None,
        "imagen_producto_path": "",
        "origen_contenido": "fecha_especial",
        "fecha_especial_nombre": special_date["nombre"],
        "prioridad": special_date["prioridad"],
    }


def _build_best_seller_copy(product: dict, brand_name: str) -> dict:
    product_name = product.get("producto_nombre") or "Producto destacado"
    category_name = product.get("categoria_nombre") or ""
    sold = product.get("total_vendido")
    price_label = _format_money(product.get("precio_valor"))
    sold_label = f" Con {sold} unidades movidas, " if sold not in (None, "") else " "
    price_line = f" Precio de referencia: {price_label}." if price_label else ""
    category_line = f" dentro de {category_name}" if category_name else ""

    return {
        "tipo": "producto_destacado",
        "titulo": f"{product_name}{' en tendencia' if not category_name else f' lidera {category_name}'}",
        "texto": (
            f"{product_name} viene mostrando muy buen movimiento{category_line}.{sold_label}"
            f"{brand_name} puede usarlo para atraer consultas y cerrar ventas más rápido.{price_line}"
        ).strip(),
        "hashtags": _clean_hashtags("#masvendido #productoestrella #ventas", "#nexarcomercio"),
        "cta": "Consultá stock y precio",
        "producto_asociado": product,
        "categoria_asociada": {"categoria_nombre": category_name} if category_name else None,
        "imagen_producto_path": product.get("imagen_producto_path", ""),
        "origen_contenido": "producto_mas_vendido",
        "fecha_especial_nombre": "",
        "prioridad": "",
    }


def _build_high_stock_copy(product: dict, brand_name: str) -> dict:
    product_name = product.get("producto_nombre") or "Producto con stock"
    stock = product.get("stock_valor")
    stock_line = f" Hay {stock} unidades disponibles." if stock not in (None, "") else ""
    category_name = product.get("categoria_nombre") or ""
    category_line = f" dentro de {category_name}" if category_name else ""
    return {
        "tipo": "promocion",
        "titulo": f"Stock listo: {product_name}",
        "texto": (
            f"{product_name} tiene disponibilidad para impulsar una promo rápida{category_line}."
            f"{stock_line} {brand_name} puede destacarlo para mover consultas esta semana."
        ).strip(),
        "hashtags": _clean_hashtags("#stockalto #promoactiva #consultanos", "#nexarcomercio"),
        "cta": "Pedilo hoy por mensaje",
        "producto_asociado": product,
        "categoria_asociada": {"categoria_nombre": category_name} if category_name else None,
        "imagen_producto_path": product.get("imagen_producto_path", ""),
        "origen_contenido": "producto_stock_alto",
        "fecha_especial_nombre": "",
        "prioridad": "",
    }


def _build_low_movement_copy(product: dict, brand_name: str) -> dict:
    product_name = product.get("producto_nombre") or "Producto por reactivar"
    category_name = product.get("categoria_nombre") or ""
    category_line = f" de la línea {category_name}" if category_name else ""
    return {
        "tipo": "recordatorio",
        "titulo": f"Volvé a mostrar {product_name}",
        "texto": (
            f"{product_name}{category_line} puede ganar visibilidad con una publicación de recordatorio, "
            f"beneficios claros y respuesta rápida desde {brand_name}."
        ),
        "hashtags": _clean_hashtags("#reactivarventas #recordatorio #negocioactivo", "#nexarcomercio"),
        "cta": "Consultanos por este producto",
        "producto_asociado": product,
        "categoria_asociada": {"categoria_nombre": category_name} if category_name else None,
        "imagen_producto_path": product.get("imagen_producto_path", ""),
        "origen_contenido": "producto_bajo_movimiento",
        "fecha_especial_nombre": "",
        "prioridad": "",
    }


def _build_category_copy(category: dict, brand_name: str) -> dict:
    category_name = category.get("categoria_nombre") or "Categoria destacada"
    return {
        "tipo": "novedad",
        "titulo": f"{category_name} para recomendar esta semana",
        "texto": (
            f"Armá una publicación enfocada en {category_name}, mostrando variedad, beneficios y propuestas "
            f"concretas para que {brand_name} active más consultas."
        ),
        "hashtags": _clean_hashtags("#categoria #novedad #ventaslocales", "#nexarcomercio"),
        "cta": "Pedinos opciones disponibles",
        "producto_asociado": None,
        "categoria_asociada": category,
        "imagen_producto_path": "",
        "origen_contenido": "categoria_destacada",
        "fecha_especial_nombre": "",
        "prioridad": "",
    }


def _build_manual_item_copy(product: dict, brand_name: str, profile: dict) -> dict:
    product_name = product.get("producto_nombre") or "Servicio destacado"
    item_type = product.get("tipo") or "producto"
    goal = _business_goal(profile)
    tone = _tone_line(profile)
    audience = str(profile.get("publico_objetivo") or "tu audiencia ideal").strip()
    category_name = product.get("categoria_nombre") or ""
    price_label = _format_money(product.get("precio_valor"))
    price_line = f" Valor de referencia: {price_label}." if price_label else ""
    stock = product.get("stock_valor")
    stock_line = f" Hay {stock} disponibles." if stock not in (None, "") and item_type == "producto" else ""
    category_line = f" dentro de {category_name}" if category_name else ""
    descriptor = "este producto" if item_type == "producto" else "este servicio"
    proposal = str(profile.get("propuesta_valor") or "").strip()
    proposal_line = f" {proposal}." if proposal else ""

    return {
        "tipo": "producto_destacado" if item_type == "producto" else "novedad",
        "titulo": f"{product_name}: propuesta para {audience}",
        "texto": (
            f"{product_name}{category_line} es una opcion concreta para {audience}. "
            f"Con una comunicacion {tone}, ayuda a avanzar sobre el objetivo de {goal}."
            f"{stock_line}{price_line}{proposal_line}"
        ).strip(),
        "hashtags": _clean_hashtags("#catalogo #negociolocal #marketing", "#manual"),
        "cta": "Consultanos y te asesoramos",
        "producto_asociado": product,
        "categoria_asociada": {"categoria_nombre": category_name} if category_name else None,
        "imagen_producto_path": product.get("imagen_producto_path", ""),
        "origen_contenido": "catalogo_manual",
        "fecha_especial_nombre": "",
        "prioridad": "",
    }


def _build_manual_category_copy(category: dict, brand_name: str, profile: dict) -> dict:
    category_name = category.get("categoria_nombre") or "Servicios destacados"
    goal = _business_goal(profile)
    return {
        "tipo": "novedad",
        "titulo": f"Semana de {category_name}",
        "texto": (
            f"{category_name} reune opciones relevantes para que {brand_name} comunique su oferta y avance sobre el objetivo de {goal}."
        ),
        "hashtags": _clean_hashtags("#categoria #catalogo #contenidodigital", "#manual"),
        "cta": "Pedinos opciones según lo que necesitás",
        "producto_asociado": None,
        "categoria_asociada": category,
        "imagen_producto_path": "",
        "origen_contenido": "categoria_manual",
        "fecha_especial_nombre": "",
        "prioridad": "",
    }


def _build_manual_goal_copy(brand_name: str, profile: dict) -> dict:
    goal = _business_goal(profile)
    audience = str(profile.get("publico_objetivo") or "tu público objetivo").strip()
    proposal = str(profile.get("propuesta_valor") or "tu diferencial").strip()
    return {
        "tipo": "promocion",
        "titulo": f"Objetivo del mes: {goal}",
        "texto": (
            f"{audience} puede encontrar en {brand_name} una propuesta clara basada en {proposal}. "
            f"El proximo paso es escribir para recibir mas informacion."
        ),
        "hashtags": _clean_hashtags("#objetivocomercial #marca #contenido", "#manual"),
        "cta": "Escribinos y te contamos más",
        "producto_asociado": None,
        "categoria_asociada": None,
        "imagen_producto_path": "",
        "origen_contenido": "objetivo_manual",
        "fecha_especial_nombre": "",
        "prioridad": "",
    }


def _build_tip_copy(brand_name: str) -> dict:
    return {
        "tipo": "tip",
        "titulo": "Tip para vender mejor por redes",
        "texto": (
            f"Un beneficio puntual de {brand_name} puede ayudar a resolver una consulta concreta. "
            "Las publicaciones claras facilitan que la audiencia de el proximo paso."
        ),
        "hashtags": "#tip #contenidocomercial #ventas",
        "cta": "Guardalo para aplicarlo",
        "producto_asociado": None,
        "categoria_asociada": None,
        "imagen_producto_path": "",
        "origen_contenido": "tip_generico",
        "fecha_especial_nombre": "",
        "prioridad": "",
    }


def _build_promo_copy(brand_name: str) -> dict:
    return {
        "tipo": "promocion",
        "titulo": f"Promo simple para activar {brand_name}",
        "texto": (
            "Una accion clara, con respuesta por mensaje y un beneficio facil de entender, "
            "puede generar movimiento aunque no haya datos comerciales disponibles."
        ),
        "hashtags": "#promo #oferta #compralocal",
        "cta": "Escribinos para aprovecharla",
        "producto_asociado": None,
        "categoria_asociada": None,
        "imagen_producto_path": "",
        "origen_contenido": "promocion_generica",
        "fecha_especial_nombre": "",
        "prioridad": "",
    }


def _resolve_manual_publication(brand_name: str, external_context: dict, slot_index: int) -> dict:
    profile = external_context.get("business_profile") or {}
    featured = external_context.get("productos_destacados") or []
    products = external_context.get("productos") or []
    categories = external_context.get("categorias") or []

    rotated = [
        MANUAL_PRIORITIES[(slot_index + offset) % len(MANUAL_PRIORITIES)]
        for offset in range(len(MANUAL_PRIORITIES))
    ]

    for priority in rotated:
        if priority == "catalogo_destacado":
            product = _pick(featured, slot_index)
            if product:
                return _build_manual_item_copy(product, brand_name, profile)
        if priority == "catalogo_general":
            product = _pick(products, slot_index)
            if product:
                return _build_manual_item_copy(product, brand_name, profile)
        if priority == "categoria_manual":
            category = _pick(categories, slot_index)
            if category:
                return _build_manual_category_copy(category, brand_name, profile)
        if priority == "objetivo_manual":
            return _build_manual_goal_copy(brand_name, profile)
        if priority == "tip_generico":
            return _build_tip_copy(brand_name)
        if priority == "promocion_generica":
            return _build_promo_copy(brand_name)

    return _build_promo_copy(brand_name)


def resolver_publicacion(
    current_date: date,
    brand_name: str,
    external_context: dict,
    slot_index: int,
) -> dict:
    special_date = obtener_fecha_especial(current_date)
    if special_date:
        return _build_special_copy(special_date, brand_name)

    if external_context.get("source") == "manual" and (
        external_context.get("productos") or external_context.get("business_profile")
    ):
        return _resolve_manual_publication(brand_name, external_context, slot_index)

    rotated = [
        COMMERCIAL_PRIORITIES[(slot_index + offset) % len(COMMERCIAL_PRIORITIES)]
        for offset in range(len(COMMERCIAL_PRIORITIES))
    ]

    products_best = external_context.get("productos_mas_vendidos") or []
    products_stock = external_context.get("productos_stock_alto") or []
    products_low = external_context.get("productos_bajo_movimiento") or []
    categories = external_context.get("categorias") or []

    for priority in rotated:
        if priority == "producto_mas_vendido":
            product = _pick(products_best, slot_index)
            if product:
                return _build_best_seller_copy(product, brand_name)
        if priority == "producto_stock_alto":
            product = _pick(products_stock, slot_index)
            if product:
                return _build_high_stock_copy(product, brand_name)
        if priority == "producto_bajo_movimiento":
            product = _pick(products_low, slot_index)
            if product:
                return _build_low_movement_copy(product, brand_name)
        if priority == "categoria_destacada":
            category = _pick(categories, slot_index)
            if category:
                return _build_category_copy(category, brand_name)
        if priority == "tip_generico":
            return _build_tip_copy(brand_name)
        if priority == "promocion_generica":
            return _build_promo_copy(brand_name)

    return _build_promo_copy(brand_name)
