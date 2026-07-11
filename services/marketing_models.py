from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class MarketingBrief:
    objective: str
    strategy: str
    funnel_stage: str
    channel: str
    content_type: str
    tone: str
    audience: str
    product_service_context: str
    value_proposition: str
    allowed_facts: tuple[str, ...] = field(default_factory=tuple)
    cta_intent: str = ""
    hashtag_topics: tuple[str, ...] = field(default_factory=tuple)
    visual_direction: str = ""


@dataclass(frozen=True, slots=True)
class GeneratedContent:
    title: str
    caption: str
    cta: str
    hashtags: tuple[str, ...]
    visual_headline: str
    visual_subtitle: str
    visual_cta: str
    strategy_used: str
    provider: str
    model: str

    def hashtags_text(self) -> str:
        return " ".join(self.hashtags)

    def public_text(self) -> str:
        parts = [self.caption.strip(), self.cta.strip(), self.hashtags_text().strip()]
        return "\n\n".join(part for part in parts if part)
