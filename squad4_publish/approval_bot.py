"""
Telegram approval bot for Squad 4.

Sends one message per content piece with [✅ Approve] [❌ Skip] inline buttons,
then polls getUpdates until every piece has a decision or the timeout expires.
Uses the shared TELEGRAM_BOT_TOKEN (the dashboard bot) so no extra bot is needed.

Pieces dict format:  {piece_key: {"label": str, "preview": str}}
Returns:             {piece_key: True/False}  (True = approved)
"""

import json
import logging
import time
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, APPROVAL_TIMEOUT_SECS

log = logging.getLogger(__name__)

_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def _api(method: str, **kwargs) -> dict:
    try:
        resp = requests.post(f"{_BASE}/{method}", json=kwargs, timeout=10)
        return resp.json()
    except Exception as e:
        log.warning("Telegram API call %s failed: %s", method, e)
        return {}


def _clear_pending_updates() -> int:
    """Advance the update offset past any queued updates so old callbacks don't fire."""
    data = _api("getUpdates", timeout=0)
    updates = data.get("result", [])
    if not updates:
        return 0
    return updates[-1]["update_id"] + 1


def _send_approval_message(piece_key: str, label: str, preview: str) -> int | None:
    """Send a piece preview with Approve/Skip buttons. Returns message_id."""
    text = (
        f"*{label}*\n\n"
        f"{preview[:400]}{'…' if len(preview) > 400 else ''}\n\n"
        "_Approve to post, Skip to discard._"
    )
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Approve", "callback_data": f"approve:{piece_key}"},
            {"text": "❌ Skip",    "callback_data": f"skip:{piece_key}"},
        ]]
    }
    result = _api(
        "sendMessage",
        chat_id=TELEGRAM_CHAT_ID,
        text=text,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
    msg = result.get("result", {})
    return msg.get("message_id")


def _edit_decision(message_id: int, label: str, approved: bool):
    """Replace the inline keyboard with the recorded decision."""
    icon = "✅" if approved else "❌"
    action = "Approved" if approved else "Skipped"
    _api(
        "editMessageText",
        chat_id=TELEGRAM_CHAT_ID,
        message_id=message_id,
        text=f"{icon} *{label}* — {action}.",
        parse_mode="Markdown",
    )


def request_approvals(pieces: dict) -> dict:
    """
    pieces: {piece_key: {"label": str, "preview": str}}
    Returns: {piece_key: bool}  True = approved, False = skipped/timed-out
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("Telegram not configured — auto-approving all pieces.")
        return {k: True for k in pieces}

    # Clear stale updates
    offset = _clear_pending_updates()

    # Send approval messages
    message_ids = {}
    for key, info in pieces.items():
        mid = _send_approval_message(key, info["label"], info["preview"])
        if mid:
            message_ids[key] = mid
            log.info("Sent approval request for %s (msg_id=%s)", key, mid)
        time.sleep(0.3)

    decisions = {}
    deadline = time.time() + APPROVAL_TIMEOUT_SECS
    pending = set(pieces.keys())

    log.info("Waiting up to %ds for %d approval(s)...", APPROVAL_TIMEOUT_SECS, len(pending))

    while pending and time.time() < deadline:
        data = _api("getUpdates", offset=offset, timeout=20)
        for update in data.get("result", []):
            offset = update["update_id"] + 1
            cb = update.get("callback_query")
            if not cb:
                continue
            _api("answerCallbackQuery", callback_query_id=cb["id"])
            action, _, key = cb.get("data", "::").partition(":")
            if key not in pending:
                continue
            approved = action == "approve"
            decisions[key] = approved
            pending.discard(key)
            if key in message_ids:
                _edit_decision(message_ids[key], pieces[key]["label"], approved)
            log.info("%s → %s", key, "APPROVED" if approved else "SKIPPED")

    # Anything still pending after timeout = skipped
    for key in pending:
        log.warning("%s timed out — skipping.", key)
        decisions[key] = False
        if key in message_ids:
            _edit_decision(message_ids[key], pieces[key]["label"], approved=False)

    return decisions
