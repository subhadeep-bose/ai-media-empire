"""
Weekly trend digest — sends a Telegram text summary of each niche's current
skip-streak state from analytics_history.json, separate from Squad 6's daily
skip-streak boost logic (squad6_analytics/analytics_run.py). The history file
only tracks a running streak per niche, not a day-by-day series, so this is a
snapshot of where each niche stands today rather than a multi-day trend line.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ANALYTICS_SKIP_STREAK_THRESHOLD
from squad6_analytics.analytics_run import load_history

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("trend_digest")

TELEGRAM_API = "https://api.telegram.org"


def build_summary(history: dict) -> str:
    if not history:
        return "Weekly Trend Digest\n\nNo niche history recorded yet."

    healthy = sorted(n for n, r in history.items() if r.get("skip_streak", 0) == 0)
    quiet = sorted(history.items(), key=lambda kv: -kv[1].get("skip_streak", 0))
    quiet = [(n, r) for n, r in quiet if r.get("skip_streak", 0) > 0]

    lines = ["Weekly Trend Digest", ""]
    if healthy:
        lines.append(f"Producing content normally: {', '.join(healthy)}")
    if quiet:
        lines.append("Going quiet:")
        for niche, record in quiet:
            streak = record.get("skip_streak", 0)
            flag = " (boosted)" if streak >= ANALYTICS_SKIP_STREAK_THRESHOLD else ""
            lines.append(f"  - {niche}: {streak} run(s) thin{flag}")
    return "\n".join(lines)


def send_telegram(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set — skipping trend digest send")
        return
    try:
        resp = requests.post(
            f"{TELEGRAM_API}/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": text},
            timeout=10,
        )
        resp.raise_for_status()
        log.info("Sent weekly trend digest to Telegram")
    except requests.RequestException:
        log.exception("Failed to send weekly trend digest")


def main():
    history = load_history()
    summary = build_summary(history)
    log.info("\n%s", summary)
    send_telegram(summary)


if __name__ == "__main__":
    main()
