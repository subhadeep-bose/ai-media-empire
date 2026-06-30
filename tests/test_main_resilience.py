"""Tests for main.py — self-healing retry orchestration."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import main


def test_run_squad_succeeds_first_try():
    with patch("main._run_once", return_value=(True, "")) as mock_run, \
         patch("main.time.sleep") as mock_sleep:
        result = main.run_squad("fake.py", "Squad X")
    assert result is True
    mock_run.assert_called_once()
    mock_sleep.assert_not_called()


def test_run_squad_recovers_after_retry():
    with patch("main._run_once", side_effect=[(False, "boom"), (True, "")]) as mock_run, \
         patch("main.time.sleep") as mock_sleep:
        result = main.run_squad("fake.py", "Squad X")
    assert result is True
    assert mock_run.call_count == 2
    mock_sleep.assert_called_once()


def test_run_squad_gives_up_after_exhausting_retries():
    with patch("main._run_once", return_value=(False, "boom")) as mock_run, \
         patch("main.time.sleep") as mock_sleep:
        result = main.run_squad("fake.py", "Squad X")
    assert result is False
    assert mock_run.call_count == main.SQUAD_RETRY_ATTEMPTS + 1
    assert mock_sleep.call_count == main.SQUAD_RETRY_ATTEMPTS


def test_run_squad_backoff_increases_with_attempt():
    waits = []
    with patch("main._run_once", return_value=(False, "boom")), \
         patch("main.time.sleep", side_effect=lambda s: waits.append(s)):
        main.run_squad("fake.py", "Squad X")
    assert waits == sorted(waits)
    assert all(w > 0 for w in waits)
