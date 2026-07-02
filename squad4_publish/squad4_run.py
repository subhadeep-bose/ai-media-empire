"""
Squad 4 — Publishing Engine
Reads Squad 2 bundle → Telegram approval → posts approved pieces:
  • Twitter thread  — tweet 1 with hero image, tweets 2-7 plain text
  • Twitter hot take — standalone tweet with hot-take card (posted immediately)
  • Twitter weekly poll — Monday only, no image (posted immediately)
Hot take is also staged to pending_hot_take.json by Squad 2 for the
delayed-post workflow (tweet_hot_take.yml) which fires 6h later.
Thread tweet-1 ID is appended to thread_history.json for weekly pin rotation.
"""

import json
import logging
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

from config import OUTPUT_DIR, SKIP_MARKERS, THREAD_HISTORY_PATH, REPO_ROOT
from reports.report_card import render_report_card
import telegram_bot
from runtime_args import get_date_str
from squad4_publish.tweet_card import render_hero_card, render_hot_take_card
from squad4_publish.approval_bot import request_approvals
from squad4_publish.twitter_publisher import post_thread, post_hot_take, post_poll


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
    import re
    # Split on lines that are purely dashes (--- or ——— etc.) possibly surrounded by whitespace
    parts = re.split(r"\n\s*-{3,}\s*\n", thread_text)
    if len(parts) == 1:
        # Fallback: LLM used Tweet 1: / Tweet 2: labels instead of separators
        parts = re.split(r"\n(?=Tweet\s+\d+[:/])", thread_text)
    return [t.strip() for t in parts if t.strip()]


def _is_skipped(content: str) -> bool:
    return any(marker in content for marker in SKIP_MARKERS) or content.startswith("[ERROR]")


SQUAD4_OUTPUT_DIR = REPO_ROOT / "squad4_output"


def _save_cards(date_str: str, tweets: list[str], hot_take: str) -> Path:
    """
    Render and save tweet cards + plain-text files to squad4_output/<date>/.
    Returns the output directory path.
    Always runs regardless of posting success so the zip always contains cards.
    """
    out = SQUAD4_OUTPUT_DIR / date_str
    out.mkdir(parents=True, exist_ok=True)

    # Hero card — tweet 1
    if tweets:
        try:
            hero = render_hero_card(tweets[0])
            (out / "01_hero_card_tweet1.png").write_bytes(hero)
            log.info("Saved hero card (%dKB)", len(hero) // 1024)
        except Exception:
            log.exception("Hero card render failed — skipping image")

    # Hot take card
    if hot_take:
        try:
            ht = render_hot_take_card(hot_take)
            (out / "02_hot_take_card.png").write_bytes(ht)
            log.info("Saved hot-take card (%dKB)", len(ht) // 1024)
        except Exception:
            log.exception("Hot-take card render failed — skipping image")

    # Plain-text tweet files for manual copy-paste
    if tweets:
        tweet_lines = []
        for i, t in enumerate(tweets, 1):
            tweet_lines.append(f"TWEET {i}/{len(tweets)}:\n{t}")
        (out / "tweets.txt").write_text("\n\n---\n\n".join(tweet_lines), encoding="utf-8")

    if hot_take:
        (out / "hot_take.txt").write_text(hot_take, encoding="utf-8")

    log.info("Squad 4 cards saved → %s", out)
    return out


def _record_thread_id(date_str: str, tweet_id: str) -> None:
    """Append {date, tweet_id} to thread_history.json for pin rotation."""
    history = []
    if THREAD_HISTORY_PATH.exists():
        try:
            history = json.loads(THREAD_HISTORY_PATH.read_text(encoding="utf-8"))
        except Exception:
            history = []
    history = [e for e in history if e.get("date") != date_str]
    history.append({"date": date_str, "tweet_id": tweet_id})
    THREAD_HISTORY_PATH.write_text(
        json.dumps(history, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    log.info("Thread ID recorded for pin rotation → %s", tweet_id)


def main():
    date_str = get_date_str()
    log.info("SQUAD 4: Publishing — %s", date_str)

    bundle = _load_bundle(date_str)
    scripts = bundle.get("scripts", {})

    twitter_text  = scripts.get("Twitter Thread (AI/Tech)", "")
    hot_take_text = scripts.get("Twitter Hot Take", "")
    poll_text     = scripts.get("Twitter Weekly Poll", "")

    # ── Build publishable pieces for approval ─────────────────────────────
    publishable = {}

    if twitter_text and not _is_skipped(twitter_text):
        tweets = _parse_tweets(twitter_text)
        if tweets:
            publishable["twitter_thread"] = {
                "label": f"Twitter Thread ({len(tweets)} tweets)",
                "preview": twitter_text[:500],
            }

    if hot_take_text and not _is_skipped(hot_take_text):
        publishable["twitter_hot_take"] = {
            "label": "Twitter Hot Take (standalone)",
            "preview": hot_take_text,
        }

    if poll_text and not _is_skipped(poll_text):
        try:
            poll_data = json.loads(poll_text)
            publishable["twitter_poll"] = {
                "label": "Twitter Weekly Poll (Monday)",
                "preview": f"{poll_data['question']}\n" + "\n".join(f"• {o}" for o in poll_data["options"]),
            }
        except (json.JSONDecodeError, KeyError):
            log.warning("Poll JSON malformed — skipping")

    # ── Save cards to squad4_output/ for artifact zip (always, before approval) ──
    thread_tweets = _parse_tweets(twitter_text) if (twitter_text and not _is_skipped(twitter_text)) else []
    ht_text = hot_take_text if (hot_take_text and not _is_skipped(hot_take_text)) else ""
    _save_cards(date_str, thread_tweets, ht_text)

    if not publishable:
        log.info("Nothing to publish today.")
        render_report_card(
            "squad4_publish", date_str,
            stats={"Pieces Sent": 0, "Approved": 0, "Posted": 0},
            items=[{"tag": "info", "text": "All pieces skipped or missing today"}],
            note="No publishable content today.",
        )
        return

    # ── Telegram approval gate ─────────────────────────────────────────────
    log.info("Requesting Telegram approval for %d piece(s)...", len(publishable))
    decisions = request_approvals(publishable)

    posted_count = 0
    items = []

    # ── Twitter thread ─────────────────────────────────────────────────────
    if decisions.get("twitter_thread"):
        tweets = thread_tweets
        hero_path = SQUAD4_OUTPUT_DIR / date_str / "01_hero_card_tweet1.png"
        hero = hero_path.read_bytes() if hero_path.exists() else None
        if not hero:
            log.warning("Hero card not found on disk — posting thread without image")

        ok, tweet_1_id = post_thread(tweets, hero_image=hero)
        tag = "twitter_thread"
        if ok:
            posted_count += 1
            items.append({"tag": tag, "text": f"{len(tweets)} tweets — tweet 1 with hero card, rest plain text"})
            if tweet_1_id:
                _record_thread_id(date_str, tweet_1_id)
        else:
            items.append({"tag": tag, "text": "FAILED — check logs"})
    else:
        items.append({"tag": "twitter_thread", "text": "skipped by user"})

    # ── Hot take ───────────────────────────────────────────────────────────
    if decisions.get("twitter_hot_take"):
        ht_path = SQUAD4_OUTPUT_DIR / date_str / "02_hot_take_card.png"
        ht_image = ht_path.read_bytes() if ht_path.exists() else None
        if not ht_image:
            log.warning("Hot-take card not found on disk — posting without image")

        ok = post_hot_take(ht_text, image=ht_image)
        if ok:
            posted_count += 1
            items.append({"tag": "hot_take", "text": "posted with hot-take card"})
        else:
            items.append({"tag": "hot_take", "text": "FAILED — check logs"})
    elif "twitter_hot_take" in publishable:
        items.append({"tag": "hot_take", "text": "skipped by user"})

    # ── Weekly poll ────────────────────────────────────────────────────────
    if decisions.get("twitter_poll"):
        try:
            poll_data = json.loads(poll_text)
            ok = post_poll(poll_data["question"], poll_data["options"])
            if ok:
                posted_count += 1
                items.append({"tag": "poll", "text": f"posted: {poll_data['question'][:60]}"})
            else:
                items.append({"tag": "poll", "text": "FAILED — check logs"})
        except Exception:
            log.exception("Poll post failed")
            items.append({"tag": "poll", "text": "FAILED — malformed poll data"})
    elif "twitter_poll" in publishable:
        items.append({"tag": "poll", "text": "skipped by user"})

    # ── Report card ────────────────────────────────────────────────────────
    approved = sum(1 for v in decisions.values() if v)
    render_report_card(
        "squad4_publish", date_str,
        stats={"Pieces Sent": len(publishable), "Approved": approved, "Posted": posted_count},
        items=items,
        note=f"{posted_count}/{len(publishable)} piece(s) posted after Telegram approval.",
    )
    telegram_bot.send_agent_update("squad4_publish", date_str)


if __name__ == "__main__":
    main()
