"""
Tweet card renderer — two layouts:
  render_hero_card()     — tweet 1: large text, bold, full attention-grab (1200x675)
  render_hot_take_card() — standalone hot take: warm red palette to distinguish from thread cards
  render_tweet_card()    — dispatcher kept for backward compat; always hero for tweet 1

Brand defaults live in config.py and are overridable via env vars.
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

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


_COLOR_DEFAULTS = {
    "bg":     "#0D1117",
    "accent": "#6C63FF",
    "text":   "#FFFFFF",
}

def _hex_to_rgb(hex_color: str, fallback: str = "#FFFFFF") -> tuple:
    h = (hex_color or fallback).lstrip("#")
    if len(h) != 6:
        h = fallback.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _png_bytes(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_hero_card(tweet_text: str) -> bytes:
    """
    Tweet 1 hero layout — full-bleed, large text, no tweet counter.
    This is the scroll-stopper; it stands alone visually.
    """
    W, H = TWEET_CARD_WIDTH, TWEET_CARD_HEIGHT
    bg = _hex_to_rgb(BRAND_BG_COLOR, "#0D1117")
    accent = _hex_to_rgb(BRAND_ACCENT_COLOR, "#6C63FF")
    white = _hex_to_rgb(BRAND_TEXT_COLOR, "#FFFFFF")
    muted = tuple(min(255, c + 45) for c in bg)

    img = Image.new("RGB", (W, H), color=bg)
    draw = ImageDraw.Draw(img)

    # Subtle dot-grid texture
    for x in range(0, W, 36):
        for y in range(0, H, 36):
            draw.ellipse([(x, y), (x + 1, y + 1)], fill=tuple(min(255, c + 12) for c in bg))

    # Bold top accent bar
    draw.rectangle([(0, 0), (W, 6)], fill=accent)

    # Left accent stripe
    draw.rectangle([(0, 0), (10, H)], fill=accent)

    # Accent glow
    for i in range(30):
        alpha = max(0, 80 - i * 3)
        col = tuple(int(c * alpha / 255 + bg[j] * (1 - alpha / 255)) for j, c in enumerate(accent))
        draw.rectangle([(10, 0), (10 + i, H)], fill=col)

    label_font = _load_font(22)
    draw.text((30, 20), "A I / T E C H  T H R E A D", font=label_font, fill=accent)

    body_font = _load_font(54)
    margin = 30
    wrapped = textwrap.fill(tweet_text, width=36)
    lines = wrapped.split("\n")

    line_h = 70
    block_h = len(lines) * line_h
    y_start = max(80, (H - block_h) // 2)

    for i, line in enumerate(lines):
        draw.text((margin + 16, y_start + i * line_h), line, font=body_font, fill=white)

    footer_y = H - 72
    draw.rectangle([(0, footer_y), (W, H)], fill=tuple(max(0, c - 5) for c in bg))
    draw.line([(0, footer_y), (W, footer_y)], fill=accent, width=2)

    handle_font = _load_font(30)
    handle = BRAND_HANDLE if BRAND_HANDLE else "AI Media Empire"
    draw.text((margin + 16, footer_y + 18), handle, font=handle_font, fill=accent)
    draw.text((W - 260, footer_y + 18), "🧵 Read the thread ↓", font=handle_font, fill=muted)

    return _png_bytes(img)


def render_hot_take_card(tweet_text: str) -> bytes:
    """
    Card for standalone hot-take tweets — warmer palette to visually
    distinguish them from thread cards.
    """
    W, H = TWEET_CARD_WIDTH, TWEET_CARD_HEIGHT
    bg = (18, 10, 10)
    accent = (255, 80, 80)
    white = _hex_to_rgb(BRAND_TEXT_COLOR, "#FFFFFF")
    muted = (120, 100, 100)

    img = Image.new("RGB", (W, H), color=bg)
    draw = ImageDraw.Draw(img)

    for x in range(0, W, 36):
        for y in range(0, H, 36):
            draw.ellipse([(x, y), (x + 1, y + 1)], fill=(24, 14, 14))

    draw.rectangle([(0, 0), (W, 6)], fill=accent)
    draw.rectangle([(0, 0), (10, H)], fill=accent)

    label_font = _load_font(22)
    draw.text((30, 20), "H O T  T A K E", font=label_font, fill=accent)

    body_font = _load_font(52)
    wrapped = textwrap.fill(tweet_text, width=36)
    lines = wrapped.split("\n")
    line_h = 68
    block_h = len(lines) * line_h
    y_start = max(80, (H - block_h) // 2)

    for i, line in enumerate(lines):
        draw.text((30 + 16, y_start + i * line_h), line, font=body_font, fill=white)

    footer_y = H - 72
    draw.rectangle([(0, footer_y), (W, H)], fill=(14, 7, 7))
    draw.line([(0, footer_y), (W, footer_y)], fill=accent, width=2)

    handle_font = _load_font(30)
    handle = BRAND_HANDLE if BRAND_HANDLE else "AI Media Empire"
    draw.text((30 + 16, footer_y + 18), handle, font=handle_font, fill=accent)
    draw.text((W - 200, footer_y + 18), "Fight me. 🔥", font=handle_font, fill=muted)

    return _png_bytes(img)


def render_tweet_card(tweet_text: str, tweet_num: int, total: int) -> bytes:
    """Backward-compat dispatcher — hero for tweet 1, otherwise raises (tweets 2+ are text-only)."""
    if tweet_num == 1:
        return render_hero_card(tweet_text)
    raise ValueError(f"render_tweet_card called for tweet {tweet_num} — only tweet 1 gets an image")
