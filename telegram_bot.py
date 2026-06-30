"""
telegram_bot — gives each named agent (see config.AGENT_PROFILES) its own
Telegram bot identity. Each squad calls send_agent_update() right after
render_report_card() so its report card shows up as a message from that
agent's own bot (own name/avatar in Telegram's chat list), as a PNG
screenshot of the card with the note as caption.

Best-effort and per-agent independent: an agent with no configured bot
token (config.TELEGRAM_BOT_TOKENS[agent_key]) or missing TELEGRAM_CHAT_ID
just logs a warning and skips — it never blocks the squad's own run or
any other agent's notification.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import requests

from config import AGENT_PROFILES, REPORTS_DIR, TELEGRAM_BOT_TOKENS, TELEGRAM_CHAT_ID
from reports.png_render import render_html_to_png

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("telegram_bot")

TELEGRAM_API = "https://api.telegram.org"


def send_agent_update(agent_key: str, date_str: str) -> None:
    token = TELEGRAM_BOT_TOKENS.get(agent_key, "")
    if not token or not TELEGRAM_CHAT_ID:
        log.warning("No Telegram bot token configured for %s — skipping", agent_key)
        return

    out_dir = REPORTS_DIR / date_str
    html_path = out_dir / f"{agent_key}.html"
    if not html_path.exists():
        log.warning("No report card found for %s at %s — skipping Telegram send", agent_key, html_path)
        return

    profile = AGENT_PROFILES[agent_key]
    import json
    note = ""
    json_path = out_dir / f"{agent_key}.json"
    if json_path.exists():
        note = json.loads(json_path.read_text(encoding="utf-8")).get("note", "")
    caption = f"{profile['name']} — {profile['role']}\n\n{note}"[:1024]

    png_path = render_html_to_png(html_path, out_dir / f"{agent_key}.png")
    base = f"{TELEGRAM_API}/bot{token}"

    try:
        if png_path and png_path.exists():
            with open(png_path, "rb") as f:
                resp = requests.post(
                    f"{base}/sendPhoto",
                    data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
                    files={"photo": f}, timeout=20,
                )
        else:
            resp = requests.post(
                f"{base}/sendMessage",
                data={"chat_id": TELEGRAM_CHAT_ID, "text": caption}, timeout=10,
            )
        resp.raise_for_status()
        log.info("Sent %s's update to Telegram", profile["name"])
    except requests.RequestException:
        log.exception("Failed to send %s's Telegram update", agent_key)
