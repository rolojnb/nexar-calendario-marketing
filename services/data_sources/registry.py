from __future__ import annotations

from services.data_sources.base import BusinessDataContext, empty_business_context
from services.data_sources import csv_importer, manual, nexar_comercio


DEFAULT_SOURCE = "nexar_comercio"


def load_business_context(
    source: str = DEFAULT_SOURCE,
    *,
    nexar_comercio_db_path: str = "",
    csv_path: str = "",
) -> BusinessDataContext:
    """Carga datos comerciales desde una fuente concreta.

    Este registro evita que el calendario conozca detalles de cada conector.
    El motor recibe siempre un `BusinessDataContext` normalizado.
    """

    normalized_source = (source or DEFAULT_SOURCE).strip().lower()

    if normalized_source == "nexar_comercio":
        return nexar_comercio.load_context(nexar_comercio_db_path)

    if normalized_source == "manual":
        return manual.load_context()

    if normalized_source in {"csv", "excel"}:
        return csv_importer.load_context(csv_path)

    context = empty_business_context(source=normalized_source or "unknown")
    context.metadata["error"] = "Fuente de datos no soportada"
    return context
