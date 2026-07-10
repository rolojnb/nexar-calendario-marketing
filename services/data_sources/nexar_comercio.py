from __future__ import annotations

from typing import Any

from services.data_sources.base import BusinessDataContext, ProductData, empty_business_context
from services.nexar_importer import load_external_context


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_product(item: dict[str, Any]) -> ProductData:
    return ProductData(
        producto_id=str(item.get("producto_id", "") or ""),
        nombre=str(item.get("producto_nombre", "") or item.get("nombre", "") or ""),
        categoria=str(item.get("categoria_nombre", "") or item.get("categoria", "") or ""),
        precio=_to_float(item.get("precio_valor", item.get("precio"))),
        stock=_to_float(item.get("stock_valor", item.get("stock"))),
        imagen_path=str(item.get("imagen_producto_path", item.get("imagen_path", "")) or ""),
        ventas=_to_float(item.get("total_vendido", item.get("ventas"))),
        raw=dict(item),
    )


def _normalize_products(items: list[dict[str, Any]]) -> list[ProductData]:
    return [normalize_product(item) for item in items]


def _normalize_categories(items: list[dict[str, Any]]) -> list[str]:
    categories: list[str] = []
    seen: set[str] = set()
    for item in items:
        name = str(item.get("categoria_nombre", "") or item.get("nombre", "") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        categories.append(name)
    return categories


def load_context(db_path: str = "") -> BusinessDataContext:
    legacy_context = load_external_context(db_path)
    if not legacy_context.get("available"):
        return empty_business_context(source="nexar_comercio")

    return BusinessDataContext(
        available=True,
        source="nexar_comercio",
        productos=_normalize_products(legacy_context.get("productos") or []),
        productos_destacados=_normalize_products(
            legacy_context.get("productos_destacados") or []
        ),
        productos_stock_alto=_normalize_products(
            legacy_context.get("productos_stock_alto") or []
        ),
        productos_bajo_movimiento=_normalize_products(
            legacy_context.get("productos_bajo_movimiento") or []
        ),
        productos_mas_vendidos=_normalize_products(
            legacy_context.get("productos_mas_vendidos") or []
        ),
        categorias=_normalize_categories(legacy_context.get("categorias") or []),
        tables=list(legacy_context.get("tables") or []),
        ventas_resumen=dict(legacy_context.get("ventas_resumen") or {}),
        metadata={"legacy_source": "services.nexar_importer"},
    )
