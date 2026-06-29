"""
Squad 1 — Intel & Research Scrapers
Fixes applied:
  1. Deduplication via seen_items.json (SHA256 hash per title)
  2. Rate limiting: time.sleep(2) between every request
  3. User-agent rotation: 5 rotating agents to avoid IP bans
  4. All keys loaded from .env, never hardcoded
"""

import json
import time
import random
import hashlib
import os
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── User-agent pool (rotated per request) ──────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/119 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/537.36 Chrome/118 Safari/537.36",
]

SEEN_ITEMS_PATH = Path("seen_items.json")
RATE_LIMIT_SECS = 2


def _headers():
    return {"User-Agent": random.choice(USER_AGENTS)}


def _sleep():
    time.sleep(RATE_LIMIT_SECS)


# ── Deduplication ──────────────────────────────────────────────────────────

def load_seen_items() -> set:
    if SEEN_ITEMS_PATH.exists():
        with open(SEEN_ITEMS_PATH, "r") as f:
            return set(json.load(f))
    return set()


def save_seen_items(seen: set):
    with open(SEEN_ITEMS_PATH, "w") as f:
        json.dump(list(seen), f)


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
        resp = requests.get(url, headers=_headers(), timeout=10)
        _sleep()
        soup = BeautifulSoup(resp.text, "html.parser")
        repos = soup.find_all("article", class_="Box-row")
        results = []
        for repo in repos[:5]:
            title_tag = repo.find("h2")
            title = title_tag.get_text(strip=True).replace(" ", "").replace("\n", "") if title_tag else ""
            if not title or not is_new(title, seen):
                continue
            desc_tag = repo.find("p")
            desc = desc_tag.get_text(strip=True) if desc_tag else "No description."
            results.append({"platform": "GitHub", "title": title, "summary": desc})
            mark_seen(title, seen)
        return results
    except Exception as e:
        return [{"platform": "GitHub", "error": str(e)}]


# ── Scraper: arXiv AI Papers ───────────────────────────────────────────────

def fetch_arxiv_ai_papers(seen: set) -> list:
    url = "https://export.arxiv.org/rss/cs.AI"
    try:
        resp = requests.get(url, headers=_headers(), timeout=10)
        _sleep()
        soup = BeautifulSoup(resp.text, "xml")
        items = soup.find_all("item")
        results = []
        for item in items[:5]:
            title = item.title.get_text(strip=True) if item.title else ""
            if not title or not is_new(title, seen):
                continue
            summary = item.description.get_text(strip=True)[:200] + "..." if item.description else ""
            results.append({"platform": "arXiv", "title": title, "summary": summary})
            mark_seen(title, seen)
        return results
    except Exception as e:
        return [{"platform": "arXiv", "error": str(e)}]


# ── Scraper: Reddit /r/artificial ─────────────────────────────────────────

def scrape_reddit_ai(seen: set) -> list:
    url = "https://www.reddit.com/r/artificial/.rss"
    try:
        resp = requests.get(url, headers=_headers(), timeout=10)
        _sleep()
        soup = BeautifulSoup(resp.text, "xml")
        entries = soup.find_all("entry")
        results = []
        for entry in entries[:5]:
            title = entry.title.get_text(strip=True) if entry.title else ""
            if not title or not is_new(title, seen):
                continue
            results.append({"platform": "Reddit/r/artificial", "title": title, "summary": "Community AI discussion."})
            mark_seen(title, seen)
        return results
    except Exception as e:
        return [{"platform": "Reddit/r/artificial", "error": str(e)}]


# ── Scraper: Goodreads Bengali Shelf ──────────────────────────────────────

def scrape_bengali_goodreads(seen: set) -> list:
    """
    Scrapes Bengali shelf AND fetches each book's individual page
    to get the real description and genre — prevents LLM hallucinating plot/author.
    """
    url = "https://www.goodreads.com/shelf/show/bangla"
    try:
        resp = requests.get(url, headers=_headers(), timeout=10)
        _sleep()
        soup = BeautifulSoup(resp.text, "html.parser")
        book_elements = soup.find_all("div", class_="elementList")
        results = []
        for el in book_elements[:3]:
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
                    book_resp = requests.get(book_url, headers=_headers(), timeout=10)
                    _sleep()
                    book_soup = BeautifulSoup(book_resp.text, "html.parser")
                    # Description
                    desc_tag = book_soup.find("div", {"data-testid": "description"}) or \
                               book_soup.find("div", id="description") or \
                               book_soup.find("span", class_="readable")
                    if desc_tag:
                        description = desc_tag.get_text(strip=True)[:300]
                    # Genres
                    genre_tags = book_soup.find_all("a", {"data-testid": "genreChip"}) or \
                                 book_soup.find_all("a", class_="actionLinkLite bookPageGenreLink")
                    genres = ", ".join([g.get_text(strip=True) for g in genre_tags[:3]])
                except Exception:
                    pass  # Use fallback summary if book page fetch fails

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
                "summary": summary,
            })
            mark_seen(title, seen)
        return results
    except Exception as e:
        return [{"platform": "Goodreads Bengali", "error": str(e)}]


# ── Scraper: ESPNcricinfo ──────────────────────────────────────────────────

def fetch_cricket_news(seen: set) -> list:
    url = "https://www.espncricinfo.com/rss/content/story/feeds/0.xml"
    try:
        resp = requests.get(url, headers=_headers(), timeout=10)
        _sleep()
        soup = BeautifulSoup(resp.text, "xml")
        items = soup.find_all("item")
        results = []
        for item in items[:4]:
            title = item.title.get_text(strip=True) if item.title else ""
            if not title or not is_new(title, seen):
                continue
            desc = item.description.get_text(strip=True)[:200] if item.description else ""
            results.append({"platform": "Cricket (ESPNcricinfo)", "title": title, "summary": desc})
            mark_seen(title, seen)
        return results
    except Exception as e:
        return [{"platform": "Cricket (ESPNcricinfo)", "error": str(e)}]


# ── Scraper: r/soccer ─────────────────────────────────────────────────────

def fetch_soccer_trends(seen: set) -> list:
    url = "https://www.reddit.com/r/soccer/.rss"
    try:
        resp = requests.get(url, headers=_headers(), timeout=10)
        _sleep()
        soup = BeautifulSoup(resp.text, "xml")
        entries = soup.find_all("entry")
        results = []
        for entry in entries[:4]:
            title = entry.title.get_text(strip=True) if entry.title else ""
            if not title or not is_new(title, seen):
                continue
            results.append({"platform": "Soccer (Reddit)", "title": title, "summary": "Trending football discussion."})
            mark_seen(title, seen)
        return results
    except Exception as e:
        return [{"platform": "Soccer (Reddit)", "error": str(e)}]


# ── Scraper: Wrestling Inc (WWE) ───────────────────────────────────────────

def fetch_wwe_news(seen: set) -> list:
    url = "https://www.wrestlinginc.com/feed/"
    try:
        resp = requests.get(url, headers=_headers(), timeout=10)
        _sleep()
        soup = BeautifulSoup(resp.text, "xml")
        items = soup.find_all("item")
        results = []
        for item in items[:4]:
            title = item.title.get_text(strip=True) if item.title else ""
            if not title or not is_new(title, seen):
                continue
            desc = item.description.get_text(strip=True)[:200] if item.description else ""
            results.append({"platform": "WWE (WrestlingInc)", "title": title, "summary": desc})
            mark_seen(title, seen)
        return results
    except Exception as e:
        return [{"platform": "WWE (WrestlingInc)", "error": str(e)}]


# ── Scraper: r/movies ─────────────────────────────────────────────────────

def fetch_movie_trends(seen: set) -> list:
    url = "https://www.reddit.com/r/movies/.rss"
    try:
        resp = requests.get(url, headers=_headers(), timeout=10)
        _sleep()
        soup = BeautifulSoup(resp.text, "xml")
        entries = soup.find_all("entry")
        results = []
        for entry in entries[:4]:
            title = entry.title.get_text(strip=True) if entry.title else ""
            if not title or not is_new(title, seen):
                continue
            results.append({"platform": "Movies (Reddit)", "title": title, "summary": "Trending cinema discussion."})
            mark_seen(title, seen)
        return results
    except Exception as e:
        return [{"platform": "Movies (Reddit)", "error": str(e)}]


# ── Scraper: SteamDB / r/SteamDeck ────────────────────────────────────────

def fetch_gaming_trends(seen: set) -> list:
    url = "https://www.reddit.com/r/SteamDeck/.rss"
    try:
        resp = requests.get(url, headers=_headers(), timeout=10)
        _sleep()
        soup = BeautifulSoup(resp.text, "xml")
        entries = soup.find_all("entry")
        results = []
        for entry in entries[:4]:
            title = entry.title.get_text(strip=True) if entry.title else ""
            if not title or not is_new(title, seen):
                continue
            results.append({"platform": "Gaming (SteamDeck/r)", "title": title, "summary": "Trending gaming discussion."})
            mark_seen(title, seen)
        return results
    except Exception as e:
        return [{"platform": "Gaming (SteamDeck/r)", "error": str(e)}]
