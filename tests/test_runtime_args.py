"""Tests for runtime_args.py — the shared --date CLI override."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_args import get_date_str


def test_get_date_str_defaults_to_today():
    with patch.object(sys, "argv", ["prog"]):
        result = get_date_str()
    from datetime import datetime
    assert result == datetime.now().strftime("%Y-%m-%d")


def test_get_date_str_uses_override():
    with patch.object(sys, "argv", ["prog", "--date", "2026-01-15"]):
        assert get_date_str() == "2026-01-15"


def test_get_date_str_rejects_malformed_date():
    with patch.object(sys, "argv", ["prog", "--date", "not-a-date"]):
        try:
            get_date_str()
            assert False, "expected ValueError"
        except ValueError:
            pass
