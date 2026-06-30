"""Tests for squad6_analytics/trend_digest.py — the weekly Telegram summary."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from squad6_analytics.trend_digest import build_summary


def test_build_summary_empty_history():
    assert "No niche history" in build_summary({})


def test_build_summary_lists_healthy_niches():
    history = {"sports": {"skip_streak": 0}, "movies": {"skip_streak": 0}}
    summary = build_summary(history)
    assert "movies" in summary and "sports" in summary
    assert "Going quiet" not in summary


def test_build_summary_flags_boosted_niches():
    history = {"gaming": {"skip_streak": 5}}
    summary = build_summary(history)
    assert "gaming" in summary
    assert "(boosted)" in summary
