"""
Squad 1 — Master Orchestrator
Runs all 30 scrapers, deduplicates, sends to local Ollama (with Groq fallback),
saves master_intel_digest.md for Squad 2 to consume.

LLM strategy: one call per niche group (not one giant call for all items).
This keeps each prompt well within Groq's free-tier token-per-minute limit.
"""

import json
import sys
import logging
import time
from datetime import datetime
from pathlib import Path

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

sys.path.insert(0, str(Path(__file__).parent))
from scrapers import (
    load_seen_items, save_seen_items,
    # AI/Tech
    scrape_github_trending, fetch_arxiv_ai_papers, scrape_reddit_ai,
    fetch_tldr_ai, fetch_hackernews_ai, fetch_reddit_ml,
    fetch_venturebeat_ai, fetch_mit_tech_review, fetch_reddit_localllama,
    fetch_verge_ai, fetch_bens_bites,
    fetch_huggingface_papers, fetch_simonwillison, fetch_rundown_ai, fetch_ai_supremacy,
    # Bengali Books
    scrape_bengali_goodreads,
    # Sports
    fetch_cricket_news, fetch_soccer_trends, fetch_wwe_news,
    fetch_bbc_sport, fetch_cricbuzz, fetch_reddit_cricket, fetch_reddit_wwe,
    # Movies & TV
    fetch_movie_trends, fetch_reddit_television, fetch_variety,
    fetch_hollywood_reporter, fetch_deadline,
    # Gaming
    fetch_gaming_trends, fetch_reddit_ps5, fetch_ign_gaming, fetch_eurogamer,
    fetch_pc_gamer, fetch_rock_paper_shotgun,
)
from reports.report_card import render_report_card
import telegram_bot
from runtime_args import get_date_str

# Seconds to wait between niche LLM calls to stay under Groq TPM limit
_INTER_NICHE_DELAY = 8


NICHE_PROMPT = """
You are an intel editor for a multi-niche media network.

Analyse this raw feed for the {niche} niche and produce a clean Markdown section.

RAW DATA:
{data}

RULES:
1. Remove duplicates and noise.
2. Surface the top 2–3 most interesting items only.
3. For EACH item output exactly:
   ### <Title>
   - **Source**: <platform>
   - **Key Takeaway**: <1 sentence — why this matters NOW>
   - **Hook Idea**: <punchy 45-second Reel/Short hook title>
4. Output ONLY the markdown. No greetings, no preamble, no niche header line.
"""

EDITOR_PICK_PROMPT = """
You are a chief editor. Given these niche summaries, choose the single most
viral-worthy story today across all niches and write a 2-sentence "Editor's Pick"
explaining why it wins.

SUMMARIES:
{summaries}

Output ONLY the Editor's Pick section in this format:
## Editor's Pick
<2 sentences>
"""

NICHES = [
    ("AI/Tech", None),
    ("Bengali Books", None),
    ("Sports", None),
    ("Movies & TV", None),
    ("Gaming", None),
]


def load_boosted_niches() -> set:
    if not NICHE_BOOST_PATH.exists():
        return set()
    try:
        data = json.loads(NICHE_BOOST_PATH.read_text(encoding="utf-8"))
        return set(data.get("boosted_niches", []))
    except (json.JSONDecodeError, OSError):
        log.warning("Could not read %s — no boosts applied", NICHE_BOOST_PATH)
        return set()


def main():
    date_str = get_date_str()
    log.info("SQUAD 1: Intel run — %s", datetime.now().strftime("%Y-%m-%d %H:%M"))

    seen = load_seen_items()
    log.info("%d items already seen — deduplication active", len(seen))

    boosted_niches = load_boosted_niches()
    if boosted_niches:
        log.info("Boosting scrape volume for niches gone quiet: %s", ", ".join(sorted(boosted_niches)))

    def limit_for(niche: str) -> int:
        return ITEMS_PER_SOURCE * NICHE_BOOST_MULTIPLIER if niche in boosted_niches else ITEMS_PER_SOURCE

    log.info("Running all 34 scrapers with rate limiting...")

    # ── Collect items grouped by niche ────────────────────────────────────
    niche_items = {
        "AI/Tech": (
            scrape_github_trending(seen) +
            fetch_arxiv_ai_papers(seen) +
            scrape_reddit_ai(seen) +
            fetch_tldr_ai(seen) +
            fetch_hackernews_ai(seen) +
            fetch_reddit_ml(seen) +
            fetch_venturebeat_ai(seen) +
            fetch_mit_tech_review(seen) +
            fetch_reddit_localllama(seen) +
            fetch_verge_ai(seen) +
            fetch_bens_bites(seen) +
            fetch_huggingface_papers(seen) +
            fetch_simonwillison(seen) +
            fetch_rundown_ai(seen) +
            fetch_ai_supremacy(seen)
        ),
        "Bengali Books": scrape_bengali_goodreads(seen, limit=limit_for("bengali_books")),
        "Sports": (
            fetch_cricket_news(seen, limit=limit_for("sports")) +
            fetch_soccer_trends(seen, limit=limit_for("sports")) +
            fetch_wwe_news(seen, limit=limit_for("sports")) +
            fetch_bbc_sport(seen, limit=limit_for("sports")) +
            fetch_cricbuzz(seen, limit=limit_for("sports")) +
            fetch_reddit_cricket(seen, limit=limit_for("sports")) +
            fetch_reddit_wwe(seen, limit=limit_for("sports"))
        ),
        "Movies & TV": (
            fetch_movie_trends(seen, limit=limit_for("movies")) +
            fetch_reddit_television(seen, limit=limit_for("movies")) +
            fetch_variety(seen, limit=limit_for("movies")) +
            fetch_hollywood_reporter(seen, limit=limit_for("movies")) +
            fetch_deadline(seen, limit=limit_for("movies"))
        ),
        "Gaming": (
            fetch_gaming_trends(seen, limit=limit_for("gaming")) +
            fetch_reddit_ps5(seen, limit=limit_for("gaming")) +
            fetch_ign_gaming(seen, limit=limit_for("gaming")) +
            fetch_eurogamer(seen, limit=limit_for("gaming")) +
            fetch_pc_gamer(seen, limit=limit_for("gaming")) +
            fetch_rock_paper_shotgun(seen, limit=limit_for("gaming"))
        ),
    }

    all_good = [i for items in niche_items.values() for i in items if "error" not in i]
    all_errors = [i for items in niche_items.values() for i in items if "error" in i]

    log.info("%d new items collected, %d scraper errors", len(all_good), len(all_errors))

    if all_errors:
        error_log = LOG_DIR / f"errors_{datetime.now().strftime('%Y%m%d')}.json"
        error_log.write_text(json.dumps(all_errors, indent=2), encoding="utf-8")
        log.warning("Errors logged to %s", error_log)

    if not all_good:
        log.error("No items collected. Check scraper errors. Aborting.")
        sys.exit(1)

    # ── One LLM call per niche (stays within Groq TPM) ───────────────────
    niche_sections = {}
    errors_count = 0

    for niche, items in niche_items.items():
        good = [i for i in items if "error" not in i]
        if not good:
            log.info("[%s] no items — skipping LLM call", niche)
            niche_sections[niche] = f"### {niche}\n_No content today._\n"
            continue

        log.info("[%s] calling LLM with %d items...", niche, len(good))
        prompt = NICHE_PROMPT.format(
            niche=niche,
            data=json.dumps(good, indent=2, ensure_ascii=False),
        )
        result = call_llm(prompt, max_tokens=GROQ_MAX_TOKENS_INTEL)

        if result.startswith("[ERROR]"):
            log.error("[%s] LLM error: %s", niche, result)
            errors_count += 1
            niche_sections[niche] = f"### {niche}\n_LLM error — skipped._\n"
        else:
            niche_sections[niche] = f"### {niche}\n{result}\n"
            log.info("[%s] done (%d chars)", niche, len(result))

        time.sleep(_INTER_NICHE_DELAY)

    if errors_count >= len(niche_items):
        log.error("All niche LLM calls failed. Aborting.")
        sys.exit(1)

    # ── Editor's Pick — one final small call ─────────────────────────────
    log.info("Generating Editor's Pick...")
    summaries = "\n\n".join(
        f"**{niche}**: {text[:300]}" for niche, text in niche_sections.items()
    )
    editor_pick = call_llm(
        EDITOR_PICK_PROMPT.format(summaries=summaries),
        max_tokens=200,
    )
    if editor_pick.startswith("[ERROR]"):
        log.warning("Editor's Pick LLM call failed — omitting")
        editor_pick = ""

    # ── Assemble and save digest ──────────────────────────────────────────
    digest_body = "\n".join(niche_sections.values())
    if editor_pick:
        digest_body += f"\n{editor_pick}\n"

    with open(DIGEST_PATH, "w", encoding="utf-8") as f:
        f.write(f"# Daily Intel Digest — {date_str}\n\n")
        f.write(digest_body)

    save_seen_items(seen)

    log.info("Digest saved to %s", DIGEST_PATH)
    log.info("%d total items in dedup index", len(seen))
    log.info("DIGEST PREVIEW (first 500 chars): %s ...", digest_body[:500])

    render_report_card(
        "squad1_intel",
        date_str,
        stats={
            "Items Collected": len(all_good),
            "Scraper Errors": len(all_errors),
            "Dedup Index": len(seen),
            "Boosted Niches": len(boosted_niches),
        },
        items=[{"tag": e.get("platform", "?"), "text": e.get("error", "")} for e in all_errors[:5]]
              or [{"tag": "ok", "text": f"{len(all_good)} fresh items across {len(niche_items)} niches"}],
        note="Boosted scrape volume for: " + ", ".join(sorted(boosted_niches))
             if boosted_niches else "All niches scraping at normal volume today.",
    )
    telegram_bot.send_agent_update("squad1_intel", date_str)


if __name__ == "__main__":
    main()
