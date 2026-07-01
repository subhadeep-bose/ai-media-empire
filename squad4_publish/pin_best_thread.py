"""
Weekly pin rotation — called by pin_best_thread.yml every Sunday at 18:00 UTC.
Reads thread_history.json (last 7 entries), fetches impression counts via
Twitter API v2 public_metrics, and pins the best-performing thread's tweet 1.

Falls back to a Telegram notification with the top tweet ID if the account
is on free tier (pin API requires Basic tier, $100/month).
"""

import json
import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
log = logging.getLogger(__name__)

from config import THREAD_HISTORY_PATH, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from squad4_publish.twitter_publisher import get_tweet_impressions, pin_tweet


def _notify_telegram(message: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        import urllib.request, urllib.parse
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": TELEGRAM_CHAT_ID, "text": message}).encode()
        urllib.request.urlopen(url, data=data, timeout=15)
    except Exception:
        log.warning("Telegram notification failed")


def main():
    if not THREAD_HISTORY_PATH.exists():
        log.info("No thread history found at %s — nothing to pin.", THREAD_HISTORY_PATH)
        sys.exit(0)

    history = json.loads(THREAD_HISTORY_PATH.read_text(encoding="utf-8"))
    recent = history[-7:]  # last 7 entries (one per day)

    if not recent:
        log.info("Thread history is empty.")
        sys.exit(0)

    tweet_ids = [e["tweet_id"] for e in recent if e.get("tweet_id")]
    log.info("Fetching impressions for %d thread(s)...", len(tweet_ids))

    impressions = get_tweet_impressions(tweet_ids)
    log.info("Impressions: %s", impressions)

    best_id = max(tweet_ids, key=lambda tid: impressions.get(tid, 0))
    best_count = impressions.get(best_id, 0)
    best_entry = next((e for e in recent if e["tweet_id"] == best_id), {})

    log.info("Best thread: %s (date=%s, impressions=%d)", best_id, best_entry.get("date"), best_count)

    pinned = pin_tweet(best_id)
    if pinned:
        msg = (
            f"📌 Weekly pin rotation complete.\n"
            f"Pinned thread from {best_entry.get('date', 'unknown')} "
            f"({best_count:,} impressions)\n"
            f"https://twitter.com/i/web/status/{best_id}"
        )
        log.info(msg)
        _notify_telegram(msg)
    else:
        msg = (
            f"📊 Best thread this week: {best_entry.get('date', 'unknown')} "
            f"({best_count:,} impressions)\n"
            f"Pin manually → https://twitter.com/i/web/status/{best_id}\n"
            f"(Auto-pin requires Twitter Basic tier)"
        )
        log.warning("Auto-pin failed — notifying via Telegram")
        _notify_telegram(msg)


if __name__ == "__main__":
    main()
