from __future__ import annotations


class ContentProviderError(Exception):
    """Base error for local and future AI content providers."""


class UnknownContentProviderError(ContentProviderError):
    """Raised when the configured content provider is not registered."""
