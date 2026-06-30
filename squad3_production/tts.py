"""
TTS wrapper around edge-tts.
Converts a script string → .mp3 file using Microsoft neural voices.
Each niche gets a distinct voice for brand consistency.
"""

import asyncio
import logging
import re
import time
from pathlib import Path

log = logging.getLogger(__name__)

TTS_RETRY_ATTEMPTS = 3
TTS_RETRY_WAIT_BASE_SECS = 5

NICHE_VOICES = {
    "ai_tech":       "en-US-GuyNeural",
    "sports":        "en-US-DavisNeural",
    "bengali_books": "en-GB-SoniaNeural",
    "movies":        "en-US-AriaNeural",
    "gaming":        "en-US-TonyNeural",
    "newsletter":    "en-US-ChristopherNeural",
    "twitter":       "en-US-GuyNeural",
    "default":       "en-US-JennyNeural",
}


def _clean_script(script: str) -> str:
    """Strip stage directions like [HOOK 0-3s] before sending to TTS."""
    script = re.sub(r"\[.*?\]:?", "", script)         # remove [HOOK 0-3s]: etc.
    script = re.sub(r"\(.*?\)", "", script)          # remove (parentheticals)
    script = re.sub(r"\n{3,}", "\n\n", script)       # collapse blank lines
    return script.strip()


async def _synthesise(text: str, voice: str, output_path: Path) -> None:
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))


def generate_audio(script: str, niche: str, output_path: Path) -> bool:
    """
    Synthesise speech for script and save to output_path (.mp3).
    Returns True on success, False on failure.
    """
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        log.warning("edge-tts not installed — skipping TTS. Run: pip install edge-tts")
        return False

    voice = NICHE_VOICES.get(niche, NICHE_VOICES["default"])
    cleaned = _clean_script(script)
    if not cleaned:
        log.warning("Empty script after cleaning for niche=%s", niche)
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, TTS_RETRY_ATTEMPTS + 1):
        try:
            asyncio.run(_synthesise(cleaned, voice, output_path))
            size_kb = output_path.stat().st_size // 1024
            log.info("TTS: %s → %s (%dKB, voice=%s)", niche, output_path.name, size_kb, voice)
            return True
        except Exception:
            if attempt < TTS_RETRY_ATTEMPTS:
                wait = TTS_RETRY_WAIT_BASE_SECS * attempt
                log.warning("TTS failed for niche=%s (attempt %d/%d) — retrying in %ds",
                            niche, attempt, TTS_RETRY_ATTEMPTS, wait)
                time.sleep(wait)
            else:
                log.exception("TTS failed for niche=%s — all %d attempts exhausted",
                               niche, TTS_RETRY_ATTEMPTS)

    return False


def generate_srt(script: str, output_path: Path, wpm: int = 150) -> None:
    """
    Generate a basic SRT caption file by estimating word timing at wpm words/minute.
    Not frame-perfect — good enough for manual adjustment in CapCut/DaVinci.
    """
    cleaned = _clean_script(script)
    words = cleaned.split()
    seconds_per_word = 60 / wpm

    chunks, chunk, duration = [], [], 0.0
    for word in words:
        chunk.append(word)
        duration += seconds_per_word
        if len(chunk) >= 8 or duration >= 3.0:
            chunks.append(" ".join(chunk))
            chunk = []
            duration = 0.0
    if chunk:
        chunks.append(" ".join(chunk))

    def _ts(secs: float) -> str:
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        s = int(secs % 60)
        ms = int((secs - int(secs)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines, t = [], 0.0
    for i, chunk_text in enumerate(chunks, 1):
        word_count = len(chunk_text.split())
        end = t + word_count * seconds_per_word
        lines.append(f"{i}\n{_ts(t)} --> {_ts(end)}\n{chunk_text}\n")
        t = end

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    log.info("SRT: %s (%d captions)", output_path.name, len(chunks))
