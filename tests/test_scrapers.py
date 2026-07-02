"""
Unit tests for squad1_intel/scrapers.py
"""

import sys
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Also add squad1_intel so scrapers can be imported directly
SQUAD1_DIR = REPO_ROOT / "squad1_intel"
if str(SQUAD1_DIR) not in sys.path:
    sys.path.insert(0, str(SQUAD1_DIR))

from scrapers import hash_title, is_new, mark_seen, _truncate
from config import SUMMARY_MAX_CHARS


# ── hash_title ─────────────────────────────────────────────────────────────

def test_hash_title_deterministic():
    """Same title with different case/whitespace produces the same hash."""
    assert hash_title("Hello World") == hash_title("hello world")
    assert hash_title("  Hello World  ") == hash_title("hello world")
    assert hash_title("HELLO WORLD") == hash_title("hello world")


def test_hash_title_length():
    h = hash_title("anything")
    assert len(h) == 16


# ── is_new / mark_seen ─────────────────────────────────────────────────────

def test_is_new_empty_seen():
    seen: set = set()
    assert is_new("Brand new title", seen) is True


def test_is_new_already_seen():
    seen: set = set()
    mark_seen("Some Title", seen)
    assert is_new("Some Title", seen) is False


def test_mark_seen_adds_hash():
    seen: set = set()
    mark_seen("My Title", seen)
    assert hash_title("My Title") in seen


def test_case_insensitive_dedup():
    seen: set = set()
    mark_seen("GPT-4 Released", seen)
    # Variant with different case should NOT be considered new
    assert is_new("gpt-4 released", seen) is False
    assert is_new("GPT-4 RELEASED", seen) is False


# ── summary truncation ─────────────────────────────────────────────────────

def test_summary_truncation_long():
    long_text = "x" * (SUMMARY_MAX_CHARS + 50)
    result = _truncate(long_text)
    assert len(result) <= SUMMARY_MAX_CHARS
    assert result.endswith("...")


def test_summary_truncation_short():
    short_text = "Short summary."
    result = _truncate(short_text)
    assert result == short_text


def test_summary_truncation_exact_boundary():
    exact = "a" * SUMMARY_MAX_CHARS
    result = _truncate(exact)
    assert result == exact
    assert len(result) == SUMMARY_MAX_CHARS


# ── scraper error format ───────────────────────────────────────────────────

def test_github_scraper_returns_error_on_exception():
    """When requests.get raises, scraper returns a list with an error dict."""
    from scrapers import scrape_github_trending

    with patch("scrapers.requests.get", side_effect=ConnectionError("timeout")):
        seen: set = set()
        results = scrape_github_trending(seen)

    assert len(results) == 1
    assert "error" in results[0]
    assert results[0]["platform"] == "GitHub"


# ── Techmeme scraper ───────────────────────────────────────────────────────

def test_techmeme_returns_results():
    """Techmeme scraper parses RSS <item> elements correctly."""
    from scrapers import fetch_techmeme

    fake_rss = """<?xml version="1.0"?>
    <rss><channel>
      <item><title>Anthropic Launches Claude Fable 5</title><description>A new model.</description></item>
      <item><title>OpenAI Ships GPT-5</title><description>Big release.</description></item>
    </channel></rss>"""

    mock_resp = MagicMock()
    mock_resp.text = fake_rss
    with patch("scrapers.requests.get", return_value=mock_resp), \
         patch("scrapers.time.sleep"):
        seen: set = set()
        results = fetch_techmeme(seen)

    assert len(results) >= 1
    assert results[0]["platform"] == "Techmeme"
    assert "Claude" in results[0]["title"] or "OpenAI" in results[0]["title"]


def test_techmeme_dedup():
    """Techmeme scraper skips already-seen titles."""
    from scrapers import fetch_techmeme, mark_seen

    fake_rss = """<?xml version="1.0"?>
    <rss><channel>
      <item><title>Already Seen Story</title><description>Old news.</description></item>
    </channel></rss>"""

    mock_resp = MagicMock()
    mock_resp.text = fake_rss
    with patch("scrapers.requests.get", return_value=mock_resp), \
         patch("scrapers.time.sleep"):
        seen: set = set()
        mark_seen("Already Seen Story", seen)
        results = fetch_techmeme(seen)

    assert results == []


def test_techmeme_error_handling():
    """Techmeme scraper returns error dict on network failure."""
    from scrapers import fetch_techmeme

    with patch("scrapers.requests.get", side_effect=ConnectionError("timeout")):
        seen: set = set()
        results = fetch_techmeme(seen)

    assert len(results) == 1
    assert "error" in results[0]
    assert results[0]["platform"] == "Techmeme"


# ── r/singularity scraper ──────────────────────────────────────────────────

def test_reddit_singularity_returns_results():
    """r/singularity scraper parses Atom feed entries correctly."""
    from scrapers import fetch_reddit_singularity

    fake_atom = """<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <title>Claude Fable 5 is insane</title>
        <content>Just tried it and the coding is next level.</content>
      </entry>
      <entry>
        <title>AGI might be closer than we think</title>
        <content>New benchmarks show surprising results.</content>
      </entry>
    </feed>"""

    mock_resp = MagicMock()
    mock_resp.text = fake_atom
    with patch("scrapers.requests.get", return_value=mock_resp), \
         patch("scrapers.time.sleep"):
        seen: set = set()
        results = fetch_reddit_singularity(seen)

    assert len(results) >= 1
    assert results[0]["platform"] == "Reddit/r/singularity"


def test_reddit_singularity_dedup():
    """r/singularity scraper skips already-seen titles."""
    from scrapers import fetch_reddit_singularity, mark_seen

    fake_atom = """<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <title>Old Breaking AI News</title>
        <content>Already processed yesterday.</content>
      </entry>
    </feed>"""

    mock_resp = MagicMock()
    mock_resp.text = fake_atom
    with patch("scrapers.requests.get", return_value=mock_resp), \
         patch("scrapers.time.sleep"):
        seen: set = set()
        mark_seen("Old Breaking AI News", seen)
        results = fetch_reddit_singularity(seen)

    assert results == []


def test_reddit_singularity_error_handling():
    """r/singularity scraper returns error dict on network failure."""
    from scrapers import fetch_reddit_singularity

    with patch("scrapers.requests.get", side_effect=ConnectionError("timeout")):
        seen: set = set()
        results = fetch_reddit_singularity(seen)

    assert len(results) == 1
    assert "error" in results[0]
    assert results[0]["platform"] == "Reddit/r/singularity"
