"""Tests for dashboard.py"""

import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import dashboard


SAMPLE_REPORTS = {
    "squad1_intel": {
        "stats": {"Items Collected": 12, "Boosted Niches": 1},
        "items": [{"tag": "ok", "text": "12 fresh items"}],
        "note": "All niches scraping normally.",
    },
    "squad2_reels": {
        "stats": {"Reels Written": 4},
        "items": [{"tag": "gaming", "text": "reel ready"}],
        "note": "4/5 reels ready.",
    },
}


def test_build_dashboard_html_includes_stats_and_items():
    out = dashboard.build_dashboard_html("2026-06-30", SAMPLE_REPORTS)
    assert "Items Collected" in out
    assert "12" in out
    assert "Reels Written" in out
    assert "reel ready" in out
    assert "All niches scraping normally." in out


def test_build_dashboard_html_escapes_content():
    reports = {
        "squad1_intel": {
            "stats": {}, "items": [{"tag": "ok", "text": "<script>alert(1)</script>"}],
            "note": "fine",
        },
    }
    out = dashboard.build_dashboard_html("2026-06-30", reports)
    assert "<script>alert(1)</script>" not in out
    assert "&lt;script&gt;" in out


def test_build_dashboard_html_handles_no_reports():
    out = dashboard.build_dashboard_html("2026-06-30", {})
    assert "No agents reported today." in out
    assert "No items today." in out


def test_render_dashboard_png_returns_none_without_playwright(tmp_path):
    html_path = tmp_path / "dashboard.html"
    html_path.write_text("<html></html>", encoding="utf-8")
    png_path = tmp_path / "dashboard.png"

    with patch.dict(sys.modules, {"playwright.sync_api": None}):
        result = dashboard.render_dashboard_png(html_path, png_path)

    assert result is None


def test_build_dashboard_writes_html_file(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "REPORTS_DIR", tmp_path)
    with patch.object(dashboard, "load_agent_reports", return_value=SAMPLE_REPORTS), \
         patch.object(dashboard, "render_dashboard_png", return_value=None):
        html_path, png_path = dashboard.build_dashboard("2026-06-30")

    assert html_path.exists()
    assert png_path is None
    assert "Items Collected" in html_path.read_text(encoding="utf-8")
