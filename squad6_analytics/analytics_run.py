"""
Squad 6 — Analytics Feedback Loop
Reads Squad 3's per-niche results, tracks consecutive skip streaks per
niche in analytics_history.json, and writes niche_boosts.json listing
niches that have gone quiet for ANALYTICS_SKIP_STREAK_THRESHOLD+ runs in a
row. Squad 1 reads that file the next run and scrapes more items for those
niches, closing the loop: thin content -> more scraping effort -> (hopefully)
real content again.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    ANALYTICS_HISTORY_PATH, NICHE_BOOST_PATH,
    ANALYTICS_SKIP_STREAK_THRESHOLD, OUTPUT_DIR,
)
from reports.report_card import render_report_card
import telegram_bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("squad6")

SQUAD3_OUTPUT = ANALYTICS_HISTORY_PATH.parent / "squad3_output"

# Only niches with a skip marker and a dedicated, boostable scraper qualify.
BOOSTABLE_NICHES = {"sports", "movies", "gaming", "bengali_books"}


def load_history() -> dict:
    if ANALYTICS_HISTORY_PATH.exists():
        try:
            return json.loads(ANALYTICS_HISTORY_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            log.warning("Corrupt analytics history — starting fresh")
    return {}


def save_history(history: dict) -> None:
    ANALYTICS_HISTORY_PATH.write_text(json.dumps(history, indent=2), encoding="utf-8")


def record_run(history: dict, results: dict, date_str: str) -> dict:
    """
    Update each niche's consecutive-skip streak from today's Squad 3 results.
    A niche resets to 0 the moment it produces real content, and increments
    by 1 each additional day it's skipped or errors out.
    """
    for entry in results.values():
        niche = entry.get("niche")
        if not niche or niche not in BOOSTABLE_NICHES:
            continue

        record = history.setdefault(niche, {"skip_streak": 0, "last_run": None})
        was_thin = entry.get("skipped") or entry.get("error")
        record["skip_streak"] = record["skip_streak"] + 1 if was_thin else 0
        record["last_run"] = date_str

    return history


def get_boosted_niches(history: dict) -> list:
    return sorted(
        niche for niche, record in history.items()
        if record.get("skip_streak", 0) >= ANALYTICS_SKIP_STREAK_THRESHOLD
    )


def save_boosts(boosted: list) -> None:
    NICHE_BOOST_PATH.write_text(json.dumps({"boosted_niches": boosted}, indent=2), encoding="utf-8")


def main():
    date_str = datetime.now().strftime("%Y-%m-%d")
    log.info("SQUAD 6: Analytics feedback loop — %s", date_str)

    results_path = SQUAD3_OUTPUT / date_str / "_results.json"
    if not results_path.exists():
        bundles = sorted(SQUAD3_OUTPUT.glob("*/_results.json"), reverse=True)
        if not bundles:
            log.warning("No Squad 3 results found — nothing to analyse. Skipping.")
            return
        results_path = bundles[0]
        log.warning("Today's results not found — using %s", results_path)

    results = json.loads(results_path.read_text(encoding="utf-8"))

    history = load_history()
    history = record_run(history, results, date_str)
    save_history(history)

    boosted = get_boosted_niches(history)
    save_boosts(boosted)

    if boosted:
        log.info("Boosting scrape volume next run for: %s", ", ".join(boosted))
    else:
        log.info("No niches need a scrape boost right now.")

    render_report_card(
        "squad6_analytics", date_str,
        stats={"Niches Tracked": len(history), "Boosted Niches": len(boosted)},
        items=[{"tag": niche, "text": f"skip streak: {record.get('skip_streak', 0)}"}
               for niche, record in sorted(history.items())],
        note="Boosting scrape volume for: " + ", ".join(boosted)
             if boosted else "All tracked niches are producing content normally.",
    )
    telegram_bot.send_agent_update("squad6_analytics", date_str)


if __name__ == "__main__":
    main()
