"""
Squad 1 — Master Orchestrator
Runs all 8 scrapers, deduplicates, sends to local Ollama (with Groq fallback),
saves master_intel_digest.md for Squad 2 to consume.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).parent.parent
load_dotenv(REPO_ROOT / ".env")

from scrapers import (
    load_seen_items, save_seen_items,
    scrape_github_trending, fetch_arxiv_ai_papers, scrape_reddit_ai,
    scrape_bengali_goodreads, fetch_cricket_news, fetch_soccer_trends,
    fetch_wwe_news, fetch_movie_trends, fetch_gaming_trends,
)

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LOG_DIR = REPO_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)


# ── LLM: Ollama with Groq fallback ────────────────────────────────────────

def call_ollama(prompt: str) -> str:
    try:
        import ollama
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        return response["message"]["content"]
    except Exception as e:
        print(f"[WARN] Ollama failed: {e}. Trying Groq fallback...")
        return call_groq(prompt)


def call_groq(prompt: str) -> str:
    if not GROQ_API_KEY:
        return "[ERROR] Both Ollama and Groq unavailable. Add GROQ_API_KEY to .env"
    try:
        import requests
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama3-8b-8192",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000,
            },
            timeout=60,
        )
        data = resp.json()
        if "choices" not in data:
            return f"[ERROR] Groq API error: {data.get('error', data)}"
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[ERROR] Groq also failed: {e}"


# ── Master prompt ──────────────────────────────────────────────────────────

MASTER_PROMPT = """
You are the Lead Intel Orchestrator for an autonomous multi-niche media network covering:
AI/Tech, Gaming (PS5 & Steam Deck), Bengali Literature, Cricket, Football, WWE, Movies & TV.

Analyse this raw feed and produce a clean Markdown digest.

RAW DATA:
{data}

RULES:
1. Remove duplicates and noise.
2. Group items by niche: AI/Tech | Gaming | Bengali Books | Cricket | Football | WWE | Movies
3. For each niche, surface the top 2–3 most interesting items only.
4. For EACH item output:
   - **Title** (concise)
   - **Source** (platform name)
   - **Key Takeaway** (1 sentence — why this matters NOW)
   - **Hook Idea** (a punchy 45-second Reel/Short hook title, human-sounding)
5. End with a **Editor's Pick** — the single most viral-worthy topic today across all niches.
6. Output ONLY the markdown. No greetings, no preamble.
"""


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*55}")
    print(f"  SQUAD 1: Intel run — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*55}")

    seen = load_seen_items()
    print(f"[INFO] {len(seen)} items already seen — deduplication active")

    print("[INFO] Running all 9 scrapers with rate limiting...")
    raw_feed = (
        scrape_github_trending(seen) +
        fetch_arxiv_ai_papers(seen) +
        scrape_reddit_ai(seen) +
        scrape_bengali_goodreads(seen) +
        fetch_cricket_news(seen) +
        fetch_soccer_trends(seen) +
        fetch_wwe_news(seen) +
        fetch_movie_trends(seen) +
        fetch_gaming_trends(seen)
    )

    # Filter out error entries for the LLM
    good_items = [i for i in raw_feed if "error" not in i]
    error_items = [i for i in raw_feed if "error" in i]

    print(f"[INFO] {len(good_items)} new items collected, {len(error_items)} scraper errors")

    if error_items:
        error_log = LOG_DIR / f"errors_{datetime.now().strftime('%Y%m%d')}.json"
        with open(error_log, "w") as f:
            json.dump(error_items, f, indent=2)
        print(f"[WARN] Errors logged to {error_log}")

    if not good_items:
        print("[ERROR] No items collected. Check scraper errors. Aborting.")
        sys.exit(1)

    print(f"[INFO] Sending {len(good_items)} items to LLM orchestrator...")
    prompt = MASTER_PROMPT.format(data=json.dumps(good_items, indent=2, ensure_ascii=False))
    digest = call_ollama(prompt)

    # Save digest for Squad 2
    output_path = REPO_ROOT / "master_intel_digest.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# Daily Intel Digest — {datetime.now().strftime('%Y-%m-%d')}\n\n")
        f.write(digest)

    # Persist updated seen items
    save_seen_items(seen)

    print(f"\n[DONE] Digest saved to {output_path}")
    print(f"[DONE] {len(seen)} total items in dedup index")
    print("\n--- DIGEST PREVIEW (first 500 chars) ---")
    print(digest[:500])
    print("...")


if __name__ == "__main__":
    main()
