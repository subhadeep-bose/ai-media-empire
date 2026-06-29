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
