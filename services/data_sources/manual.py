from __future__ import annotations

from typing import Any

from services.data_sources.base import BusinessDataContext, ProductData, empty_business_context
from services.manual_store import get_business_profile, list_catalog_items


def normalize_product(item: dict[str, Any]) -> ProductData:
    return ProductData(
        producto_id=str(item.get("id", "") or item.get("producto_id", "") or ""),
        nombre=str(item.get("nombre", "") or item.get("producto_nombre", "") or ""),
        descripcion=str(item.get("descripcion", "") or ""),
        categoria=str(item.get("categoria", "") or item.get("categoria_nombre", "") or ""),
        tipo=str(item.get("item_type", item.get("tipo", "producto")) or "producto"),
        precio=float(item["precio"]) if item.get("precio") not in (None, "") else None,
        stock=float(item["stock"]) if item.get("stock") not in (None, "") else None,
        imagen_path=str(item.get("image_path", item.get("imagen_producto_path", "")) or ""),
        ventas=None,
        destacado=bool(item.get("featured", item.get("destacado", False))),
        activo=bool(item.get("active", item.get("activo", True))),
        raw=dict(item),
    )


def load_context(db_path: str = "") -> BusinessDataContext:
    if not db_path:
        return empty_business_context(source="manual")

    profile = get_business_profile(db_path)
    items = list_catalog_items(db_path, include_inactive=False)
    active_items = [item for item in items if not item.get("deleted_at")]
    if not profile["nombre_comercial"] and not active_items:
        return empty_business_context(
            source="manual",
            has_profile=False,
            has_catalog=False,
        )

    normalized_items = [normalize_product(item) for item in active_items]
    featured_items = [item for item in normalized_items if item.destacado] or normalized_items
    stock_items = [
        item for item in normalized_items
        if item.stock is not None and item.tipo == "producto"
    ]
    stock_items.sort(key=lambda item: item.stock or 0, reverse=True)

    categories: list[str] = []
    seen: set[str] = set()
    for item in normalized_items:
        category = item.categoria.strip()
        if not category or category in seen:
            continue
        seen.add(category)
        categories.append(category)

    return BusinessDataContext(
        available=bool(profile["nombre_comercial"] or normalized_items),
        source="manual",
        business_profile=profile,
        productos=normalized_items,
        productos_destacados=featured_items,
        productos_stock_alto=stock_items,
        productos_bajo_movimiento=[],
        productos_mas_vendidos=[],
        categorias=categories,
        tables=["business_profile", "catalog_items"],
        metadata={
            "has_profile": bool(profile["nombre_comercial"]),
            "has_catalog": bool(normalized_items),
            "catalog_total": len(normalized_items),
        },
    )
