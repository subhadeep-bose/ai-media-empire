"""Tests for usage_tracker.py — daily Groq token usage tracking."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import usage_tracker


def test_record_and_get_usage_accumulates(tmp_path, monkeypatch):
    monkeypatch.setattr(usage_tracker, "LLM_USAGE_PATH", tmp_path / "usage.json")

    usage_tracker.record_groq_usage("2026-06-30", 100)
    usage_tracker.record_groq_usage("2026-06-30", 50)

    assert usage_tracker.get_usage("2026-06-30") == 150


def test_record_groq_usage_ignores_zero_tokens(tmp_path, monkeypatch):
    usage_path = tmp_path / "usage.json"
    monkeypatch.setattr(usage_tracker, "LLM_USAGE_PATH", usage_path)

    usage_tracker.record_groq_usage("2026-06-30", 0)

    assert not usage_path.exists()


def test_get_usage_returns_zero_for_unknown_date(tmp_path, monkeypatch):
    monkeypatch.setattr(usage_tracker, "LLM_USAGE_PATH", tmp_path / "usage.json")
    assert usage_tracker.get_usage("2026-01-01") == 0
