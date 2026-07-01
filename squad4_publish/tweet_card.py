"""
Tweet card renderer — produces a branded 1200x675 PNG for each tweet.

Brand defaults are set in config.py and can be overridden via env vars.
Tries to load a system TrueType font; falls back to PIL's built-in default.
"""

import textwrap
from io import BytesIO
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PIL import Image, ImageDraw, ImageFont
from config import (
    BRAND_BG_COLOR, BRAND_ACCENT_COLOR, BRAND_TEXT_COLOR,
    BRAND_HANDLE, TWEET_CARD_WIDTH, TWEET_CARD_HEIGHT,
)

# Candidate system font paths (Ubuntu/Debian → macOS → fallback)
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    # Pillow 10+ default supports size kwarg
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def render_tweet_card(tweet_text: str, tweet_num: int, total: int) -> bytes:
    """
    Render a branded quote card for a single tweet.
    Returns PNG bytes ready to upload to Twitter.
    """
    W, H = TWEET_CARD_WIDTH, TWEET_CARD_HEIGHT
    bg = _hex_to_rgb(BRAND_BG_COLOR)
    accent = _hex_to_rgb(BRAND_ACCENT_COLOR)
    text_col = _hex_to_rgb(BRAND_TEXT_COLOR)
    muted = tuple(min(255, c + 40) for c in bg)

    img = Image.new("RGB", (W, H), color=bg)
    draw = ImageDraw.Draw(img)

    # Left accent stripe
    draw.rectangle([(0, 0), (10, H)], fill=accent)

    # Tweet counter badge top-right
    badge_font = _load_font(28)
    counter = f"{tweet_num} / {total}"
    draw.text((W - 90, 30), counter, font=badge_font, fill=muted)

    # Main tweet text — wrap to fit
    body_font = _load_font(48)
    margin = 60
    max_width = W - margin * 2 - 10  # account for accent stripe
    wrapped = textwrap.fill(tweet_text, width=42)

    # Centre text block vertically
    lines = wrapped.split("\n")
    line_h = 58
    block_h = len(lines) * line_h
    y_start = (H - block_h) // 2 - 20

    for i, line in enumerate(lines):
        draw.text((margin + 10, y_start + i * line_h), line, font=body_font, fill=text_col)

    # Divider line above footer
    footer_y = H - 70
    draw.line([(margin, footer_y), (W - margin, footer_y)], fill=accent, width=2)

    # Handle / branding bottom-left
    handle_font = _load_font(32)
    handle_text = BRAND_HANDLE if BRAND_HANDLE else "AI Media Empire"
    draw.text((margin + 10, footer_y + 18), handle_text, font=handle_font, fill=accent)

    # "AI/Tech Daily" label bottom-right
    draw.text((W - 240, footer_y + 18), "AI/Tech Daily", font=handle_font, fill=muted)

    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
