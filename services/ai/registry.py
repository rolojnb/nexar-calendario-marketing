from __future__ import annotations

from services.ai.base import ContentProvider
from services.ai.deterministic import DeterministicContentProvider
from services.ai.exceptions import UnknownContentProviderError


_PROVIDERS: dict[str, type[ContentProvider]] = {
    DeterministicContentProvider.provider_name: DeterministicContentProvider,
}


def get_content_provider(name: str = "deterministic") -> ContentProvider:
    provider_class = _PROVIDERS.get((name or "deterministic").strip().lower())
    if not provider_class:
        raise UnknownContentProviderError(f"Proveedor de contenido no registrado: {name}")
    return provider_class()
