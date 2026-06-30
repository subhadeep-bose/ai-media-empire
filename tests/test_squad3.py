"""Tests for Squad 3 — TTS helpers and metadata parsing."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from squad3_production.tts import _clean_script, generate_srt, generate_audio, NICHE_VOICES


# ── TTS helpers ──────────────────────────────────────────────────────────────

def test_clean_script_removes_stage_directions():
    script = "[HOOK 0-3s]: This is real content. [CTA 40-45s]: Follow me."
    result = _clean_script(script)
    assert "[HOOK" not in result
    assert "[CTA" not in result
    assert "This is real content." in result


def test_clean_script_removes_parentheticals():
    script = "This is great (pause here) content."
    result = _clean_script(script)
    assert "(pause here)" not in result
    assert "This is great" in result


def test_clean_script_empty_input():
    assert _clean_script("") == ""
    assert _clean_script("[HOOK]: [CTA]:") == ""


def test_niche_voices_all_present():
    required = ["ai_tech", "sports", "bengali_books", "movies", "gaming", "newsletter"]
    for niche in required:
        assert niche in NICHE_VOICES, f"Missing voice for niche: {niche}"


def test_generate_srt_creates_file(tmp_path):
    script = "This is a test script with enough words to create multiple caption chunks for the SRT file."
    out = tmp_path / "captions.srt"
    generate_srt(script, out)
    assert out.exists()
    content = out.read_text()
    assert "00:00:00,000 --> " in content
    assert "1\n" in content


def test_generate_srt_chunk_count(tmp_path):
    # 80 words at 8 words/chunk = ~10 chunks
    script = " ".join(["word"] * 80)
    out = tmp_path / "captions.srt"
    generate_srt(script, out)
    content = out.read_text()
    chunks = [line for line in content.split("\n") if line.strip().isdigit()]
    assert len(chunks) >= 8


# ── Metadata ─────────────────────────────────────────────────────────────────

def test_generate_youtube_metadata_parses_json():
    from squad3_production.metadata import generate_youtube_metadata
    mock_response = json.dumps({
        "title": "AI just changed everything",
        "description": "Here is a description of the content.",
        "tags": ["ai", "tech", "news", "openai", "llm", "gpt", "claude",
                 "machine learning", "artificial intelligence", "future"],
        "category": "Science & Technology",
        "thumbnail_text": "AI changed everything",
    })
    with patch("squad3_production.metadata.call_llm", return_value=mock_response):
        result = generate_youtube_metadata("Some script content", "AI/Tech")
    assert result["title"] == "AI just changed everything"
    assert len(result["tags"]) == 10


def test_generate_youtube_metadata_handles_llm_error():
    from squad3_production.metadata import generate_youtube_metadata
    with patch("squad3_production.metadata.call_llm", return_value="[ERROR] Groq failed"):
        result = generate_youtube_metadata("script", "Gaming")
    assert "error" in result


def test_generate_youtube_metadata_handles_bad_json():
    from squad3_production.metadata import generate_youtube_metadata
    with patch("squad3_production.metadata.call_llm", return_value="not json at all"):
        result = generate_youtube_metadata("script", "Sports")
    assert "raw" in result


def test_generate_instagram_caption_returns_string():
    from squad3_production.metadata import generate_instagram_caption
    with patch("squad3_production.metadata.call_llm", return_value="Great caption here. #aitech"):
        result = generate_instagram_caption("Some script", "ai_tech")
    assert isinstance(result, str)
    assert len(result) > 0


# ── TTS retry behaviour ──────────────────────────────────────────────────────

def test_generate_audio_retries_then_succeeds(tmp_path):
    out = tmp_path / "audio.mp3"
    calls = {"n": 0}

    def fake_run(coro):
        coro.close()
        calls["n"] += 1
        if calls["n"] < 2:
            raise RuntimeError("No audio was received")
        out.write_bytes(b"x" * 2048)

    with patch("squad3_production.tts.asyncio.run", side_effect=fake_run), \
         patch("squad3_production.tts.time.sleep"):
        result = generate_audio("Some real script content", "sports", out)

    assert result is True
    assert calls["n"] == 2


def test_generate_audio_gives_up_after_max_attempts(tmp_path):
    out = tmp_path / "audio.mp3"

    def fake_run(coro):
        coro.close()
        raise RuntimeError("No audio was received")

    with patch("squad3_production.tts.asyncio.run", side_effect=fake_run), \
         patch("squad3_production.tts.time.sleep") as mock_sleep:
        result = generate_audio("Some real script content", "sports", out)

    assert result is False
    assert mock_sleep.call_count == 2
