"""
Delayed hot take poster — called by tweet_hot_take.yml (~6h after main pipeline).
Reads pending_hot_take.json written by Squad 2 and posts if the date matches today.
"""

import json
import logging
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
log = logging.getLogger(__name__)

from config import HOT_TAKE_PENDING_PATH
from squad4_publish.tweet_card import render_hot_take_card
from squad4_publish.twitter_publisher import post_hot_take


def main():
    if not HOT_TAKE_PENDING_PATH.exists():
        log.info("No pending hot take found at %s — nothing to post.", HOT_TAKE_PENDING_PATH)
        sys.exit(0)

    payload = json.loads(HOT_TAKE_PENDING_PATH.read_text(encoding="utf-8"))
    staged_date = payload.get("date", "")
    today = date.today().isoformat()

    if staged_date != today:
        log.info("Staged hot take is from %s, today is %s — skipping stale post.", staged_date, today)
        sys.exit(0)

    text = payload.get("text", "").strip()
    if not text:
        log.warning("Staged hot take has empty text — skipping.")
        sys.exit(0)

    log.info("Rendering hot-take card...")
    try:
        image = render_hot_take_card(text)
    except Exception:
        log.exception("Hot-take card render failed — posting without image")
        image = None

    log.info("Posting hot take...")
    ok = post_hot_take(text, image=image)
    if ok:
        log.info("Hot take posted successfully.")
        HOT_TAKE_PENDING_PATH.unlink(missing_ok=True)
    else:
        log.error("Hot take post failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
