from __future__ import annotations

from services.data_sources.base import BusinessDataContext, empty_business_context


def load_context() -> BusinessDataContext:
    """Fuente manual segura hasta que exista carga persistida desde UI."""

    return empty_business_context(source="manual")
