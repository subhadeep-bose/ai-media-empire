"""
Tracks Groq token usage per day in LLM_USAGE_PATH, so the Chief of Staff
roundup can surface a running total — Ollama calls are local/free and
aren't tracked. Best-effort: a write failure here must never break the
squad that's mid-LLM-call, so every operation is wrapped and logged
instead of raised.
"""

import json
import logging

from config import LLM_USAGE_PATH

log = logging.getLogger(__name__)


def record_groq_usage(date_str: str, total_tokens: int) -> None:
    if not total_tokens:
        return
    try:
        history = {}
        if LLM_USAGE_PATH.exists():
            history = json.loads(LLM_USAGE_PATH.read_text(encoding="utf-8"))
        history[date_str] = history.get(date_str, 0) + total_tokens
        LLM_USAGE_PATH.write_text(json.dumps(history, indent=2), encoding="utf-8")
    except (OSError, json.JSONDecodeError):
        log.warning("Could not update %s with today's Groq usage", LLM_USAGE_PATH)


def get_usage(date_str: str) -> int:
    if not LLM_USAGE_PATH.exists():
        return 0
    try:
        history = json.loads(LLM_USAGE_PATH.read_text(encoding="utf-8"))
        return history.get(date_str, 0)
    except (OSError, json.JSONDecodeError):
        return 0
