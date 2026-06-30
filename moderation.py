"""
Lightweight moderation pass for Squad 3, checked right before a script is
turned into audio/video. Catches an obvious LLM slip past config's
hallucination guards — not a full moderation system.
"""

from config import MODERATION_DENYLIST


def flagged_terms(text: str) -> list[str]:
    lowered = text.lower()
    return [term for term in MODERATION_DENYLIST if term in lowered]
