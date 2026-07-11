from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from services.marketing_models import GeneratedContent, MarketingBrief


class ContentProvider(ABC):
    provider_name: str
    model_name: str

    @abstractmethod
    def generate_content(
        self,
        brief: MarketingBrief,
        settings: dict[str, Any] | None = None,
    ) -> GeneratedContent:
        raise NotImplementedError
