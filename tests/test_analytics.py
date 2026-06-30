"""Tests for squad6_analytics/analytics_run.py — the niche feedback loop."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from squad6_analytics.analytics_run import record_run, get_boosted_niches, BOOSTABLE_NICHES
from config import ANALYTICS_SKIP_STREAK_THRESHOLD


def _result(niche, skipped=False, error=False):
    return {"niche": niche, "skipped": skipped, "error": error}


def test_record_run_increments_streak_on_skip():
    history = {}
    results = {"Instagram Reel (Sports)": _result("sports", skipped=True)}
    history = record_run(history, results, "2026-06-30")
    assert history["sports"]["skip_streak"] == 1


def test_record_run_resets_streak_on_real_content():
    history = {"sports": {"skip_streak": 5, "last_run": "2026-06-29"}}
    results = {"Instagram Reel (Sports)": _result("sports", skipped=False)}
    history = record_run(history, results, "2026-06-30")
    assert history["sports"]["skip_streak"] == 0


def test_record_run_ignores_non_boostable_niches():
    history = {}
    results = {"Instagram Reel (AI/Tech)": _result("ai_tech", skipped=True)}
    history = record_run(history, results, "2026-06-30")
    assert "ai_tech" not in history


def test_record_run_counts_error_as_thin_content():
    history = {}
    results = {"Instagram Reel (Movies)": _result("movies", skipped=False, error=True)}
    history = record_run(history, results, "2026-06-30")
    assert history["movies"]["skip_streak"] == 1


def test_get_boosted_niches_below_threshold_excluded():
    history = {"gaming": {"skip_streak": ANALYTICS_SKIP_STREAK_THRESHOLD - 1}}
    assert get_boosted_niches(history) == []


def test_get_boosted_niches_at_threshold_included():
    history = {"gaming": {"skip_streak": ANALYTICS_SKIP_STREAK_THRESHOLD}}
    assert get_boosted_niches(history) == ["gaming"]


def test_boostable_niches_have_dedicated_scrapers():
    assert BOOSTABLE_NICHES == {"sports", "movies", "gaming", "bengali_books"}
