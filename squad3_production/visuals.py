"""
Stock footage sourcing via Pexels video search.
Each niche maps to a search query; clips are downloaded to a per-niche
working directory for FFmpeg assembly in video.py.
"""

import logging
from pathlib import Path

import requests

from config import PEXELS_API_KEY, STOCK_CLIPS_PER_REEL

log = logging.getLogger(__name__)

PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"

NICHE_QUERIES = {
    "ai_tech":       "technology computer code",
    "sports":        "stadium sports crowd",
    "bengali_books": "books library reading",
    "movies":        "cinema film reel",
    "gaming":        "gaming setup neon",
    "default":       "abstract background motion",
}


def fetch_stock_clips(niche: str, dest_dir: Path, count: int = STOCK_CLIPS_PER_REEL) -> list:
    """
    Download up to `count` portrait stock video clips for the niche.
    Returns a list of local Paths (possibly empty if no API key or on failure —
    callers must treat an empty list as "skip video assembly", not an error).
    """
    if not PEXELS_API_KEY:
        log.warning("PEXELS_API_KEY not set — skipping stock footage fetch")
        return []

    query = NICHE_QUERIES.get(niche, NICHE_QUERIES["default"])
    try:
        resp = requests.get(
            PEXELS_SEARCH_URL,
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "per_page": count, "orientation": "portrait"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        log.exception("Pexels search failed for niche=%s", niche)
        return []

    dest_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, video in enumerate(data.get("videos", [])[:count]):
        file_url = _pick_video_file(video)
        if not file_url:
            continue
        clip_path = dest_dir / f"clip_{i}.mp4"
        if _download(file_url, clip_path):
            paths.append(clip_path)

    if not paths:
        log.warning("No usable clips downloaded for niche=%s", niche)
    return paths


def _pick_video_file(video: dict) -> str:
    """Pick the smallest file at or above 720p width to keep downloads fast."""
    files = sorted(video.get("video_files", []), key=lambda f: f.get("width") or 0)
    candidates = [f for f in files if (f.get("width") or 0) >= 720] or files
    return candidates[0]["link"] if candidates else ""


def _download(url: str, dest: Path) -> bool:
    try:
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return True
    except Exception:
        log.exception("Failed to download clip %s", url)
        return False
