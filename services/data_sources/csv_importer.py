from __future__ import annotations

from services.data_sources.base import BusinessDataContext, empty_business_context


def load_context(csv_path: str = "") -> BusinessDataContext:
    """Punto de extensión para importar productos CSV/Excel en una etapa futura."""

    return empty_business_context(source="csv", csv_path=csv_path)
