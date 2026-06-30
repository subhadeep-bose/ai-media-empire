import os
import logging
import requests
import time
from datetime import datetime

from config import GROQ_MODEL, GROQ_RATE_LIMIT_RETRIES, GROQ_RATE_LIMIT_WAIT_BASE, OLLAMA_MODEL
from usage_tracker import record_groq_usage

log = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


def call_ollama(prompt: str, max_tokens: int = 1500) -> str | None:
    try:
        import ollama
        r = ollama.chat(model=OLLAMA_MODEL, messages=[{"role": "user", "content": prompt}])
        return r["message"]["content"]
    except Exception as e:
        log.debug("Ollama unavailable: %s", e)
        return None


def call_groq(prompt: str, max_tokens: int = 1000) -> str:
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
        return "[ERROR] No GROQ_API_KEY set"
    for attempt in range(GROQ_RATE_LIMIT_RETRIES):
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
                timeout=60,
            )
            data = resp.json()
            if "choices" in data:
                tokens = data.get("usage", {}).get("total_tokens", 0)
                record_groq_usage(datetime.now().strftime("%Y-%m-%d"), tokens)
                return data["choices"][0]["message"]["content"]
            err = data.get("error", {})
            if isinstance(err, dict) and err.get("code") == "rate_limit_exceeded":
                wait = GROQ_RATE_LIMIT_WAIT_BASE * (attempt + 1)
                log.warning("Groq rate limit — waiting %ds (attempt %d/%d)", wait, attempt + 1, GROQ_RATE_LIMIT_RETRIES)
                time.sleep(wait)
                continue
            msg = err.get("message", str(data)[:200]) if isinstance(err, dict) else str(data)[:200]
            return f"[ERROR] Groq: {msg}"
        except Exception as e:
            log.exception("Groq request failed")
            return f"[ERROR] Groq exception: {e}"
    return "[ERROR] Groq rate limit exceeded after all retries"


def call_llm(prompt: str, max_tokens: int = 1000) -> str:
    result = call_ollama(prompt, max_tokens)
    if result is not None:
        return result
    return call_groq(prompt, max_tokens)
