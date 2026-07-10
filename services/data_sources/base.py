from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ProductData:
    """Producto normalizado independiente de la fuente original."""

    producto_id: str = ""
    nombre: str = ""
    categoria: str = ""
    precio: float | None = None
    stock: float | None = None
    imagen_path: str = ""
    ventas: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_legacy_dict(self) -> dict[str, Any]:
        legacy = dict(self.raw)
        legacy.update(
            {
                "producto_id": self.producto_id,
                "producto_nombre": self.nombre,
                "categoria_nombre": self.categoria,
                "precio_valor": self.precio,
                "stock_valor": self.stock,
                "imagen_producto_path": self.imagen_path,
                "total_vendido": self.ventas,
            }
        )
        return legacy


@dataclass(slots=True)
class BusinessDataContext:
    """Contexto comercial común que puede adaptarse al motor actual."""

    available: bool = False
    source: str = "none"
    productos: list[ProductData] = field(default_factory=list)
    productos_destacados: list[ProductData] = field(default_factory=list)
    productos_stock_alto: list[ProductData] = field(default_factory=list)
    productos_bajo_movimiento: list[ProductData] = field(default_factory=list)
    productos_mas_vendidos: list[ProductData] = field(default_factory=list)
    categorias: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    ventas_resumen: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_legacy_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "source": self.source,
            "tables": list(self.tables),
            "productos": [product.to_legacy_dict() for product in self.productos],
            "productos_destacados": [
                product.to_legacy_dict() for product in self.productos_destacados
            ],
            "productos_stock_alto": [
                product.to_legacy_dict() for product in self.productos_stock_alto
            ],
            "productos_bajo_movimiento": [
                product.to_legacy_dict() for product in self.productos_bajo_movimiento
            ],
            "productos_mas_vendidos": [
                product.to_legacy_dict() for product in self.productos_mas_vendidos
            ],
            "categorias": [
                {"categoria_nombre": category}
                for category in self.categorias
                if category
            ],
            "ventas_resumen": dict(self.ventas_resumen),
            "metadata": dict(self.metadata),
        }

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def empty_business_context(source: str = "none", **metadata: Any) -> BusinessDataContext:
    return BusinessDataContext(source=source, metadata=dict(metadata))
