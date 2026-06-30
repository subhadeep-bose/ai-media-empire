"""Tests for reports/report_card.py and chief_of_staff.py."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from reports.report_card import render_report_card


def test_render_report_card_writes_html_and_json(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "REPORTS_DIR", tmp_path)
    import reports.report_card as report_card
    monkeypatch.setattr(report_card, "REPORTS_DIR", tmp_path)

    html_path = render_report_card(
        "squad1_intel", "2026-06-30",
        stats={"Items Collected": 12, "Scraper Errors": 0},
        items=[{"tag": "ok", "text": "all good"}],
        note="Smooth run.",
    )

    assert html_path.exists()
    assert "Virat Kohli" in html_path.read_text(encoding="utf-8")

    json_path = tmp_path / "2026-06-30" / "squad1_intel.json"
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["name"] == "Virat Kohli"
    assert data["stats"]["Items Collected"] == 12


def test_render_report_card_escapes_html(tmp_path, monkeypatch):
    import reports.report_card as report_card
    monkeypatch.setattr(report_card, "REPORTS_DIR", tmp_path)

    html_path = render_report_card(
        "squad6_analytics", "2026-06-30",
        stats={}, items=[], note="<script>alert(1)</script>",
    )
    rendered = html_path.read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in rendered
    assert "&lt;script&gt;" in rendered


def test_render_report_card_handles_empty_items(tmp_path, monkeypatch):
    import reports.report_card as report_card
    monkeypatch.setattr(report_card, "REPORTS_DIR", tmp_path)

    html_path = render_report_card(
        "squad2_newsletter", "2026-06-30", stats={"Chars Written": 0}, items=[], note="",
    )
    assert "No items today." in html_path.read_text(encoding="utf-8")
