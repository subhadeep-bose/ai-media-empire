"""Tests for reports/png_render.py"""

import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from reports.png_render import render_html_to_png


def test_render_html_to_png_returns_none_without_playwright(tmp_path):
    html_path = tmp_path / "card.html"
    html_path.write_text("<html></html>", encoding="utf-8")
    png_path = tmp_path / "card.png"

    with patch.dict(sys.modules, {"playwright.sync_api": None}):
        result = render_html_to_png(html_path, png_path)

    assert result is None
