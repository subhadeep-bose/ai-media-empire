"""Tests for chief_of_staff.py — the daily agent-report roundup."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import chief_of_staff


def test_load_agent_reports_reads_only_existing_files(tmp_path, monkeypatch):
    monkeypatch.setattr(chief_of_staff, "REPORTS_DIR", tmp_path)
    date_dir = tmp_path / "2026-06-30"
    date_dir.mkdir()
    (date_dir / "squad1_intel.json").write_text(
        json.dumps({"name": "Virat Kohli", "note": "12 items collected"}), encoding="utf-8"
    )

    reports = chief_of_staff.load_agent_reports("2026-06-30")

    assert "squad1_intel" in reports
    assert reports["squad1_intel"]["name"] == "Virat Kohli"
    assert "squad2_newsletter" not in reports


def test_load_agent_reports_empty_when_no_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(chief_of_staff, "REPORTS_DIR", tmp_path)
    assert chief_of_staff.load_agent_reports("2026-01-01") == {}
