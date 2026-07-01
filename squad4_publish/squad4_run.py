"""
Squad 4 — Publishing Engine
Reads Squad 2 bundle → sends Telegram approval requests → posts approved
Twitter threads with branded images → renders report card.

Runs after Squad 3 in the daily pipeline.
"""

import json
import logging
import sys
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

from config import OUTPUT_DIR, SKIP_MARKERS
from reports.report_card import render_report_card
import telegram_bot
from runtime_args import get_date_str
from squad4_publish.tweet_card import render_tweet_card
from squad4_publish.approval_bot import request_approvals
from squad4_publish.twitter_publisher import post_thread


def _load_bundle(date_str: str) -> dict:
    bundle_path = OUTPUT_DIR / f"bundle_{date_str}.json"
    if not bundle_path.exists():
        bundles = sorted(OUTPUT_DIR.glob("bundle_*.json"), reverse=True)
        if not bundles:
            log.error("No Squad 2 bundle found.")
            sys.exit(1)
        bundle_path = bundles[0]
        log.warning("Today's bundle not found — using %s", bundle_path)
    return json.loads(bundle_path.read_text(encoding="utf-8"))


def _parse_tweets(thread_text: str) -> list[str]:
    """Split the thread script on '---' separators into individual tweet strings."""
    return [t.strip() for t in thread_text.split("---") if t.strip()]


def _is_skipped(content: str) -> bool:
    return any(marker in content for marker in SKIP_MARKERS)


def main():
    date_str = get_date_str()
    log.info("SQUAD 4: Publishing — %s", date_str)

    bundle = _load_bundle(date_str)
    scripts = bundle.get("scripts", {})

    # ── Identify publishable pieces ────────────────────────────────────────
    twitter_text = scripts.get("Twitter Thread (AI/Tech)", "")

    publishable = {}
    if twitter_text and not _is_skipped(twitter_text):
        publishable["twitter"] = {
            "label": "Twitter Thread (AI/Tech)",
            "preview": twitter_text[:500],
        }

    if not publishable:
        log.info("Nothing to publish today (all pieces skipped or missing).")
        render_report_card(
            "squad4_publish", date_str,
            stats={"Pieces Sent": 0, "Approved": 0, "Posted": 0},
            items=[],
            note="No publishable content today — all pieces were skipped.",
        )
        return

    # ── Telegram approval gate ─────────────────────────────────────────────
    log.info("Requesting approval via Telegram for %d piece(s)...", len(publishable))
    decisions = request_approvals(publishable)

    approved_count = sum(1 for v in decisions.values() if v)
    posted_count = 0
    items = []

    # ── Post approved Twitter thread ───────────────────────────────────────
    if decisions.get("twitter"):
        tweets = _parse_tweets(twitter_text)
        if not tweets:
            log.warning("Twitter thread parsed to 0 tweets — skipping.")
        else:
            log.info("Generating branded images for %d tweets...", len(tweets))
            images = []
            for i, tweet in enumerate(tweets):
                try:
                    images.append(render_tweet_card(tweet, i + 1, len(tweets)))
                except Exception:
                    log.exception("Card render failed for tweet %d — posting without image", i + 1)
                    images.append(None)

            clean_images = [img for img in images if img is not None]
            log.info("Posting thread (%d tweets)...", len(tweets))
            ok = post_thread(tweets, images=clean_images if clean_images else None)
            if ok:
                posted_count += 1
                log.info("Twitter thread posted successfully.")
                items.append({"tag": "twitter", "text": f"{len(tweets)} tweets posted with branded images"})
            else:
                log.error("Twitter thread posting failed.")
                items.append({"tag": "twitter", "text": "posting FAILED — check logs"})
    else:
        log.info("Twitter thread skipped by user.")
        items.append({"tag": "twitter", "text": "skipped by user"})

    # ── Report card ────────────────────────────────────────────────────────
    render_report_card(
        "squad4_publish", date_str,
        stats={
            "Pieces Sent": len(publishable),
            "Approved": approved_count,
            "Posted": posted_count,
        },
        items=items,
        note=f"{posted_count}/{len(publishable)} piece(s) posted after Telegram approval.",
    )
    telegram_bot.send_agent_update("squad4_publish", date_str)


if __name__ == "__main__":
    main()
