"""
Squad 1 — Intel & Research Scrapers
Fixes applied:
  1. Deduplication via seen_items.json (SHA256 hash per title)
  2. Rate limiting: time.sleep(RATE_LIMIT_SECS) between every request
  3. User-agent rotation: 5 rotating agents to avoid IP bans
  4. All keys loaded from environment, never hardcoded
  5. File locking for seen_items.json (fcntl on Linux, fallback for Windows)
  6. Real content extraction from Reddit RSS feeds
  7. All summaries pre-truncated to SUMMARY_MAX_CHARS
"""

import json
import time
import random
import hashlib
import logging
import sys
from pathlib import Path

# Add repo root to sys.path so config/llm imports work
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import requests
from bs4 import BeautifulSoup

from config import (
    SCRAPER_TIMEOUT,
    RATE_LIMIT_SECS,
    ITEMS_PER_SOURCE,
    SUMMARY_MAX_CHARS,
    SEEN_ITEMS_PATH,
)

log = logging.getLogger(__name__)

# ── User-agent pool (rotated per request) ──────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/119 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/537.36 Chrome/118 Safari/537.36",
]


def _headers():
    return {"User-Agent": random.choice(USER_AGENTS)}


def _sleep():
    time.sleep(RATE_LIMIT_SECS)


def _truncate(text: str) -> str:
    """Truncate text to SUMMARY_MAX_CHARS."""
    if len(text) <= SUMMARY_MAX_CHARS:
        return text
    return text[:SUMMARY_MAX_CHARS - 3] + "..."


def _strip_html(html_text: str) -> str:
    """Strip HTML tags from a string."""
    try:
        return BeautifulSoup(html_text, "html.parser").get_text(separator=" ", strip=True)
    except Exception:
        return html_text


# ── File locking for seen_items.json ──────────────────────────────────────

try:
    import fcntl

    def _lock_file(f):
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)

    def _unlock_file(f):
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

except ImportError:
    # Windows fallback — no-op
    def _lock_file(f):
        pass

    def _unlock_file(f):
        pass


# ── Deduplication ──────────────────────────────────────────────────────────

def load_seen_items() -> set:
    if SEEN_ITEMS_PATH.exists():
        try:
            with open(SEEN_ITEMS_PATH, "r") as f:
                _lock_file(f)
                data = json.load(f)
                _unlock_file(f)
                return set(data)
        except Exception:
            log.exception("Failed to load seen_items.json")
    return set()


def save_seen_items(seen: set):
    try:
        with open(SEEN_ITEMS_PATH, "w") as f:
            _lock_file(f)
            json.dump(list(seen), f)
            _unlock_file(f)
    except Exception:
        log.exception("Failed to save seen_items.json")


def hash_title(title: str) -> str:
    return hashlib.sha256(title.lower().strip().encode()).hexdigest()[:16]


def is_new(title: str, seen: set) -> bool:
    return hash_title(title) not in seen


def mark_seen(title: str, seen: set):
    seen.add(hash_title(title))


# ── Scraper: GitHub Trending ───────────────────────────────────────────────

def scrape_github_trending(seen: set) -> list:
    url = "https://github.com/trending/python?since=daily"
    try:
        resp = requests.get(url, headers=_headers(), timeout=SCRAPER_TIMEOUT)
        _sleep()
        soup = BeautifulSoup(resp.text, "html.parser")
        repos = soup.find_all("article", class_="Box-row")
        results = []
        for repo in repos[:ITEMS_PER_SOURCE]:
            title_tag = repo.find("h2")
            title = title_tag.get_text(strip=True).replace(" ", "").replace("\n", "") if title_tag else ""
            if not title or not is_new(title, seen):
                continue
            desc_tag = repo.find("p")
            desc = desc_tag.get_text(strip=True) if desc_tag else "No description."
            results.append({"platform": "GitHub", "title": title, "summary": _truncate(desc)})
            mark_seen(title, seen)
        return results
    except Exception:
        log.exception("GitHub scraper failed")
        return [{"platform": "GitHub", "error": "scraper exception"}]


# ── Scraper: arXiv AI Papers ───────────────────────────────────────────────

def fetch_arxiv_ai_papers(seen: set) -> list:
    url = "https://export.arxiv.org/rss/cs.AI"
    try:
        resp = requests.get(url, headers=_headers(), timeout=SCRAPER_TIMEOUT)
        _sleep()
        soup = BeautifulSoup(resp.text, "xml")
        items = soup.find_all("item")
        results = []
        for item in items[:ITEMS_PER_SOURCE]:
            title = item.title.get_text(strip=True) if item.title else ""
            if not title or not is_new(title, seen):
                continue
            raw = item.description.get_text(strip=True) if item.description else ""
            summary = _truncate(raw)
            results.append({"platform": "arXiv", "title": title, "summary": summary})
            mark_seen(title, seen)
        return results
    except Exception:
        log.exception("arXiv scraper failed")
        return [{"platform": "arXiv", "error": "scraper exception"}]


# ── Scraper: Reddit /r/artificial ─────────────────────────────────────────

def scrape_reddit_ai(seen: set) -> list:
    url = "https://www.reddit.com/r/artificial/.rss"
    try:
        resp = requests.get(url, headers=_headers(), timeout=SCRAPER_TIMEOUT)
        _sleep()
        soup = BeautifulSoup(resp.text, "xml")
        entries = soup.find_all("entry")
        results = []
        for entry in entries[:ITEMS_PER_SOURCE]:
            title = entry.title.get_text(strip=True) if entry.title else ""
            if not title or not is_new(title, seen):
                continue
            # Extract real content from RSS entry
            content_tag = entry.find("content") or entry.find("summary")
            if content_tag:
                raw = _strip_html(content_tag.get_text(strip=True))
            else:
                raw = "Community AI discussion."
            summary = _truncate(raw)
            results.append({"platform": "Reddit/r/artificial", "title": title, "summary": summary})
            mark_seen(title, seen)
        return results
    except Exception:
        log.exception("Reddit AI scraper failed")
        return [{"platform": "Reddit/r/artificial", "error": "scraper exception"}]


# ── Scraper: Goodreads Bengali Shelf ──────────────────────────────────────

def scrape_bengali_goodreads(seen: set, limit: int = ITEMS_PER_SOURCE) -> list:
    """
    Scrapes Bengali shelf AND fetches each book's individual page
    to get the real description and genre — prevents LLM hallucinating plot/author.
    """
    url = "https://www.goodreads.com/shelf/show/bangla"
    try:
        resp = requests.get(url, headers=_headers(), timeout=SCRAPER_TIMEOUT)
        _sleep()
        soup = BeautifulSoup(resp.text, "html.parser")
        book_elements = soup.find_all("div", class_="elementList")
        results = []
        for el in book_elements[:limit]:
            title_tag = el.find("a", class_="bookTitle") or el.find("a")
            title = title_tag.get_text(strip=True) if title_tag else ""
            book_url = "https://www.goodreads.com" + title_tag["href"] if title_tag and title_tag.get("href") else ""
            author_tag = el.find("a", class_="authorName")
            author = author_tag.get_text(strip=True) if author_tag else "Unknown author"
            if not title or not is_new(title, seen):
                continue

            # Fetch individual book page to get real description
            description = ""
            genres = ""
            if book_url:
                try:
                    book_resp = requests.get(book_url, headers=_headers(), timeout=SCRAPER_TIMEOUT)
                    _sleep()
                    book_soup = BeautifulSoup(book_resp.text, "html.parser")
                    desc_tag = book_soup.find("div", {"data-testid": "description"}) or \
                               book_soup.find("div", id="description") or \
                               book_soup.find("span", class_="readable")
                    if desc_tag:
                        description = desc_tag.get_text(strip=True)[:300]
                    genre_tags = book_soup.find_all("a", {"data-testid": "genreChip"}) or \
                                 book_soup.find_all("a", class_="actionLinkLite bookPageGenreLink")
                    genres = ", ".join([g.get_text(strip=True) for g in genre_tags[:3]])
                except Exception:
                    log.debug("Failed to fetch individual book page for %s", title)

            summary = f"Author: {author}."
            if genres:
                summary += f" Genre: {genres}."
            if description:
                summary += f" Plot: {description}"
            else:
                summary += " [Description unavailable — use only author and title in review, do not invent plot details.]"

            results.append({
                "platform": "Goodreads Bengali",
                "title": title,
                "author": author,
                "genres": genres or "Bengali fiction",
                "summary": _truncate(summary),
            })
            mark_seen(title, seen)
        return results
    except Exception:
        log.exception("Goodreads Bengali scraper failed")
        return [{"platform": "Goodreads Bengali", "error": "scraper exception"}]


# ── Scraper: ESPNcricinfo ──────────────────────────────────────────────────

def fetch_cricket_news(seen: set, limit: int = ITEMS_PER_SOURCE) -> list:
    url = "https://www.espncricinfo.com/rss/content/story/feeds/0.xml"
    try:
        resp = requests.get(url, headers=_headers(), timeout=SCRAPER_TIMEOUT)
        _sleep()
        soup = BeautifulSoup(resp.text, "xml")
        items = soup.find_all("item")
        results = []
        for item in items[:limit]:
            title = item.title.get_text(strip=True) if item.title else ""
            if not title or not is_new(title, seen):
                continue
            raw = item.description.get_text(strip=True) if item.description else ""
            results.append({"platform": "Cricket (ESPNcricinfo)", "title": title, "summary": _truncate(raw)})
            mark_seen(title, seen)
        return results
    except Exception:
        log.exception("Cricket scraper failed")
        return [{"platform": "Cricket (ESPNcricinfo)", "error": "scraper exception"}]


# ── Scraper: r/soccer ─────────────────────────────────────────────────────

def fetch_soccer_trends(seen: set, limit: int = ITEMS_PER_SOURCE) -> list:
    url = "https://www.reddit.com/r/soccer/.rss"
    try:
        resp = requests.get(url, headers=_headers(), timeout=SCRAPER_TIMEOUT)
        _sleep()
        soup = BeautifulSoup(resp.text, "xml")
        entries = soup.find_all("entry")
        results = []
        for entry in entries[:limit]:
            title = entry.title.get_text(strip=True) if entry.title else ""
            if not title or not is_new(title, seen):
                continue
            content_tag = entry.find("content") or entry.find("summary")
            if content_tag:
                raw = _strip_html(content_tag.get_text(strip=True))
            else:
                raw = "Trending football discussion."
            results.append({"platform": "Soccer (Reddit)", "title": title, "summary": _truncate(raw)})
            mark_seen(title, seen)
        return results
    except Exception:
        log.exception("Soccer scraper failed")
        return [{"platform": "Soccer (Reddit)", "error": "scraper exception"}]


# ── Scraper: Wrestling Inc (WWE) ───────────────────────────────────────────

def fetch_wwe_news(seen: set, limit: int = ITEMS_PER_SOURCE) -> list:
    url = "https://www.wrestlinginc.com/feed/"
    try:
        resp = requests.get(url, headers=_headers(), timeout=SCRAPER_TIMEOUT)
        _sleep()
        soup = BeautifulSoup(resp.text, "xml")
        items = soup.find_all("item")
        results = []
        for item in items[:limit]:
            title = item.title.get_text(strip=True) if item.title else ""
            if not title or not is_new(title, seen):
                continue
            raw = item.description.get_text(strip=True) if item.description else ""
            results.append({"platform": "WWE (WrestlingInc)", "title": title, "summary": _truncate(raw)})
            mark_seen(title, seen)
        return results
    except Exception:
        log.exception("WWE scraper failed")
        return [{"platform": "WWE (WrestlingInc)", "error": "scraper exception"}]


# ── Scraper: r/movies ─────────────────────────────────────────────────────

def fetch_movie_trends(seen: set, limit: int = ITEMS_PER_SOURCE) -> list:
    url = "https://www.reddit.com/r/movies/.rss"
    try:
        resp = requests.get(url, headers=_headers(), timeout=SCRAPER_TIMEOUT)
        _sleep()
        soup = BeautifulSoup(resp.text, "xml")
        entries = soup.find_all("entry")
        results = []
        for entry in entries[:limit]:
            title = entry.title.get_text(strip=True) if entry.title else ""
            if not title or not is_new(title, seen):
                continue
            content_tag = entry.find("content") or entry.find("summary")
            if content_tag:
                raw = _strip_html(content_tag.get_text(strip=True))
            else:
                raw = "Trending cinema discussion."
            results.append({"platform": "Movies (Reddit)", "title": title, "summary": _truncate(raw)})
            mark_seen(title, seen)
        return results
    except Exception:
        log.exception("Movies scraper failed")
        return [{"platform": "Movies (Reddit)", "error": "scraper exception"}]


# ── Scraper: TLDR AI newsletter (RSS) ────────────────────────────────────

def fetch_tldr_ai(seen: set, limit: int = ITEMS_PER_SOURCE) -> list:
    url = "https://tldr.tech/api/rss/ai"
    try:
        resp = requests.get(url, headers=_headers(), timeout=SCRAPER_TIMEOUT)
        _sleep()
        soup = BeautifulSoup(resp.text, "xml")
        items = soup.find_all("item")
        results = []
        for item in items[:limit]:
            title = item.title.get_text(strip=True) if item.title else ""
            if not title or not is_new(title, seen):
                continue
            raw = item.description.get_text(strip=True) if item.description else ""
            results.append({"platform": "TLDR AI", "title": title, "summary": _truncate(_strip_html(raw))})
            mark_seen(title, seen)
        return results
    except Exception:
        log.exception("TLDR AI scraper failed")
        return [{"platform": "TLDR AI", "error": "scraper exception"}]


# ── Scraper: Hacker News (AI stories via Algolia) ────────────────────────

def fetch_hackernews_ai(seen: set, limit: int = ITEMS_PER_SOURCE) -> list:
    url = (
        "https://hn.algolia.com/api/v1/search"
        "?query=AI+machine+learning&tags=story&hitsPerPage=10"
    )
    try:
        resp = requests.get(url, headers=_headers(), timeout=SCRAPER_TIMEOUT)
        _sleep()
        hits = resp.json().get("hits", [])
        results = []
        for hit in hits[:limit]:
            title = hit.get("title", "").strip()
            if not title or not is_new(title, seen):
                continue
            summary = _truncate(hit.get("story_text") or hit.get("url") or "Hacker News discussion.")
            results.append({"platform": "Hacker News", "title": title, "summary": _strip_html(summary)})
            mark_seen(title, seen)
        return results
    except Exception:
        log.exception("Hacker News AI scraper failed")
        return [{"platform": "Hacker News", "error": "scraper exception"}]


# ── Scraper: r/MachineLearning ────────────────────────────────────────────

def fetch_reddit_ml(seen: set, limit: int = ITEMS_PER_SOURCE) -> list:
    url = "https://www.reddit.com/r/MachineLearning/.rss"
    try:
        resp = requests.get(url, headers=_headers(), timeout=SCRAPER_TIMEOUT)
        _sleep()
        soup = BeautifulSoup(resp.text, "xml")
        entries = soup.find_all("entry")
        results = []
        for entry in entries[:limit]:
            title = entry.title.get_text(strip=True) if entry.title else ""
            if not title or not is_new(title, seen):
                continue
            content_tag = entry.find("content") or entry.find("summary")
            raw = _strip_html(content_tag.get_text(strip=True)) if content_tag else "ML research discussion."
            results.append({"platform": "Reddit/r/MachineLearning", "title": title, "summary": _truncate(raw)})
            mark_seen(title, seen)
        return results
    except Exception:
        log.exception("r/MachineLearning scraper failed")
        return [{"platform": "Reddit/r/MachineLearning", "error": "scraper exception"}]


# ── Scraper: SteamDB / r/SteamDeck ────────────────────────────────────────

def fetch_gaming_trends(seen: set, limit: int = ITEMS_PER_SOURCE) -> list:
    url = "https://www.reddit.com/r/SteamDeck/.rss"
    try:
        resp = requests.get(url, headers=_headers(), timeout=SCRAPER_TIMEOUT)
        _sleep()
        soup = BeautifulSoup(resp.text, "xml")
        entries = soup.find_all("entry")
        results = []
        for entry in entries[:limit]:
            title = entry.title.get_text(strip=True) if entry.title else ""
            if not title or not is_new(title, seen):
                continue
            content_tag = entry.find("content") or entry.find("summary")
            if content_tag:
                raw = _strip_html(content_tag.get_text(strip=True))
            else:
                raw = "Trending gaming discussion."
            results.append({"platform": "Gaming (SteamDeck/r)", "title": title, "summary": _truncate(raw)})
            mark_seen(title, seen)
        return results
    except Exception:
        log.exception("Gaming scraper failed")
        return [{"platform": "Gaming (SteamDeck/r)", "error": "scraper exception"}]
