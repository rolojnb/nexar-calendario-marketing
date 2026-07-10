from __future__ import annotations

from services.data_sources.base import BusinessDataContext, empty_business_context


def load_context() -> BusinessDataContext:
    """Fuente manual inicial.

    En una próxima etapa esta fuente podrá leer productos cargados desde la UI
    en la base local de Nexar Calendario. Por ahora devuelve un contexto vacío
    y seguro para mantener funcionando el calendario con contenido genérico.
    """

    return empty_business_context(source="manual")
