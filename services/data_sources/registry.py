from __future__ import annotations

from collections.abc import Callable

from services.data_sources.base import BusinessDataContext, empty_business_context
from services.data_sources import csv_importer, manual, nexar_comercio


DEFAULT_SOURCE = "nexar_comercio"
SUPPORTED_SOURCES = ("nexar_comercio", "manual", "csv")


def _normalise_source(source: str | None) -> str:
    return (source or DEFAULT_SOURCE).strip().lower()


def load_business_context(
    source: str = DEFAULT_SOURCE,
    *,
    nexar_comercio_db_path: str = "",
    csv_path: str = "",
) -> BusinessDataContext:
    loaders: dict[str, Callable[[], BusinessDataContext]] = {
        "nexar_comercio": lambda: nexar_comercio.load_context(nexar_comercio_db_path),
        "manual": manual.load_context,
        "csv": lambda: csv_importer.load_context(csv_path),
    }

    normalized_source = _normalise_source(source)
    loader = loaders.get(normalized_source)
    if loader:
        return loader()

    return empty_business_context(
        source=normalized_source or "unknown",
        error="Fuente de datos no soportada",
        supported_sources=list(SUPPORTED_SOURCES),
    )
