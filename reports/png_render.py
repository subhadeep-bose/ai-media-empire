"""
Shared HTML -> PNG renderer (headless Chromium via Playwright), used by
dashboard.py and telegram_bot.py to screenshot report cards for delivery
to Telegram. Best-effort: returns None instead of raising if
Playwright/Chromium isn't available, so callers can fall back to a
text-only message rather than crashing the pipeline.
"""

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def render_html_to_png(html_path: Path, png_path: Path,
                        width: int = 820, height: int = 600) -> Path | None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.warning("playwright not installed — skipping PNG render of %s", html_path)
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(html_path.resolve().as_uri())
            page.screenshot(path=str(png_path), full_page=True)
            browser.close()
        return png_path
    except Exception:
        log.exception("Failed to render PNG for %s", html_path)
        return None
