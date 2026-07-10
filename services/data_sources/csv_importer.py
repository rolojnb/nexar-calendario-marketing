from __future__ import annotations

from services.data_sources.base import BusinessDataContext, empty_business_context


def load_context(csv_path: str = "") -> BusinessDataContext:
    """Fuente CSV/Excel inicial.

    Queda como punto de extensión para importar productos desde archivos.
    En el MVP siguiente se puede implementar lectura CSV estándar y luego
    soporte Excel si se agrega una dependencia como openpyxl.
    """

    context = empty_business_context(source="csv")
    if csv_path:
        context.metadata["csv_path"] = csv_path
    return context
