"""
Squad 1 — Master Orchestrator
Runs all 9 scrapers, deduplicates, sends to local Ollama (with Groq fallback),
saves master_intel_digest.md for Squad 2 to consume.
"""

import json
import sys
import logging
from datetime import datetime
from pathlib import Path

# Add repo root to sys.path so config/llm imports work
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
log = logging.getLogger(__name__)

from config import (
    DIGEST_PATH, LOG_DIR, GROQ_MAX_TOKENS_INTEL,
    ITEMS_PER_SOURCE, NICHE_BOOST_PATH, NICHE_BOOST_MULTIPLIER,
)
from llm import call_llm

LOG_DIR.mkdir(exist_ok=True)

# Import scrapers (squad1_intel is CWD when run, so direct import works;
# also works when run from repo root because scrapers adds REPO_ROOT to path)
sys.path.insert(0, str(Path(__file__).parent))
from scrapers import (
    load_seen_items, save_seen_items,
    scrape_github_trending, fetch_arxiv_ai_papers, scrape_reddit_ai,
    scrape_bengali_goodreads, fetch_cricket_news, fetch_soccer_trends,
    fetch_wwe_news, fetch_movie_trends, fetch_gaming_trends,
)
from reports.report_card import render_report_card
import telegram_bot


def load_boosted_niches() -> set:
    """Read niches Squad 6 flagged as gone quiet for ANALYTICS_SKIP_STREAK_THRESHOLD+ runs."""
    if not NICHE_BOOST_PATH.exists():
        return set()
    try:
        data = json.loads(NICHE_BOOST_PATH.read_text(encoding="utf-8"))
        return set(data.get("boosted_niches", []))
    except (json.JSONDecodeError, OSError):
        log.warning("Could not read %s — no boosts applied", NICHE_BOOST_PATH)
        return set()


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
    log.info("SQUAD 1: Intel run — %s", datetime.now().strftime("%Y-%m-%d %H:%M"))

    seen = load_seen_items()
    log.info("%d items already seen — deduplication active", len(seen))

    boosted_niches = load_boosted_niches()
    if boosted_niches:
        log.info("Boosting scrape volume for niches gone quiet: %s", ", ".join(sorted(boosted_niches)))

    def limit_for(niche: str) -> int:
        return ITEMS_PER_SOURCE * NICHE_BOOST_MULTIPLIER if niche in boosted_niches else ITEMS_PER_SOURCE

    log.info("Running all 9 scrapers with rate limiting...")
    raw_feed = (
        scrape_github_trending(seen) +
        fetch_arxiv_ai_papers(seen) +
        scrape_reddit_ai(seen) +
        scrape_bengali_goodreads(seen, limit=limit_for("bengali_books")) +
        fetch_cricket_news(seen, limit=limit_for("sports")) +
        fetch_soccer_trends(seen, limit=limit_for("sports")) +
        fetch_wwe_news(seen, limit=limit_for("sports")) +
        fetch_movie_trends(seen, limit=limit_for("movies")) +
        fetch_gaming_trends(seen, limit=limit_for("gaming"))
    )

    good_items = [i for i in raw_feed if "error" not in i]
    error_items = [i for i in raw_feed if "error" in i]

    log.info("%d new items collected, %d scraper errors", len(good_items), len(error_items))

    if error_items:
        error_log = LOG_DIR / f"errors_{datetime.now().strftime('%Y%m%d')}.json"
        with open(error_log, "w") as f:
            json.dump(error_items, f, indent=2)
        log.warning("Errors logged to %s", error_log)

    if not good_items:
        log.error("No items collected. Check scraper errors. Aborting.")
        sys.exit(1)

    log.info("Sending %d items to LLM orchestrator...", len(good_items))
    prompt = MASTER_PROMPT.format(data=json.dumps(good_items, indent=2, ensure_ascii=False))
    digest = call_llm(prompt, max_tokens=GROQ_MAX_TOKENS_INTEL)

    if digest.startswith("[ERROR]"):
        log.error("LLM returned an error: %s", digest)
        sys.exit(1)

    with open(DIGEST_PATH, "w", encoding="utf-8") as f:
        f.write(f"# Daily Intel Digest — {datetime.now().strftime('%Y-%m-%d')}\n\n")
        f.write(digest)

    save_seen_items(seen)

    log.info("Digest saved to %s", DIGEST_PATH)
    log.info("%d total items in dedup index", len(seen))
    log.info("DIGEST PREVIEW (first 500 chars): %s ...", digest[:500])

    date_str = datetime.now().strftime("%Y-%m-%d")
    render_report_card(
        "squad1_intel",
        date_str,
        stats={
            "Items Collected": len(good_items),
            "Scraper Errors": len(error_items),
            "Dedup Index": len(seen),
            "Boosted Niches": len(boosted_niches),
        },
        items=[{"tag": e.get("platform", "?"), "text": e.get("error", "")} for e in error_items[:5]]
              or [{"tag": "ok", "text": f"{len(good_items)} fresh items sent to the digest"}],
        note="Boosted scrape volume for: " + ", ".join(sorted(boosted_niches))
             if boosted_niches else "All niches scraping at normal volume today.",
    )
    telegram_bot.send_agent_update("squad1_intel", date_str)


if __name__ == "__main__":
    main()
