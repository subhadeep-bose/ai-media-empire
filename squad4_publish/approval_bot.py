"""
Telegram approval gate for Squad 4.

request_approvals(pieces) sends one inline-keyboard message per piece,
polls getUpdates for callback_query responses, and returns a dict of
{piece_key: bool} decisions. Times out after APPROVAL_TIMEOUT_SECS (default 30 min).

If Telegram is not configured (missing bot token or chat ID) all pieces
are auto-approved so the pipeline can still run in CI without secrets.
"""

import logging
import os
import time
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

log = logging.getLogger(__name__)

from config import APPROVAL_TIMEOUT_SECS, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def _api(token: str, method: str, **params):
    import urllib.request, urllib.parse, json
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(url, data=data, timeout=30) as r:
        return json.loads(r.read())


def request_approvals(pieces: dict) -> dict:
    """
    pieces: {key: {"label": str, "preview": str}}
    Returns: {key: True/False}
    """
    token = TELEGRAM_BOT_TOKEN
    chat_id = TELEGRAM_CHAT_ID

    if not token or not chat_id:
        log.warning("Telegram not configured — auto-approving all pieces")
        return {k: True for k in pieces}

    import json

    decisions = {}
    message_map = {}  # key -> message_id

    for key, info in pieces.items():
        label = info["label"]
        preview = info["preview"][:400]
        text = f"*[Squad 4 Approval]*\n*{label}*\n\n```\n{preview}\n```"

        keyboard = json.dumps({
            "inline_keyboard": [[
                {"text": "✅ Approve", "callback_data": f"approve:{key}"},
                {"text": "❌ Skip",    "callback_data": f"skip:{key}"},
            ]]
        })

        try:
            resp = _api(token, "sendMessage",
                        chat_id=chat_id,
                        text=text,
                        parse_mode="Markdown",
                        reply_markup=keyboard)
            message_map[key] = resp["result"]["message_id"]
        except Exception:
            log.exception("Failed to send approval message for %s — auto-approving", key)
            decisions[key] = True

    pending = {k for k in pieces if k not in decisions}
    if not pending:
        return decisions

    offset = None
    deadline = time.time() + APPROVAL_TIMEOUT_SECS
    log.info("Waiting up to %ds for Telegram approval of: %s", APPROVAL_TIMEOUT_SECS, list(pending))

    while pending and time.time() < deadline:
        remaining = max(1, min(30, int(deadline - time.time())))
        params = {"timeout": remaining}
        if offset is not None:
            params["offset"] = offset

        try:
            resp = _api(token, "getUpdates", **params)
        except Exception:
            log.warning("getUpdates failed — retrying")
            time.sleep(5)
            continue

        for update in resp.get("result", []):
            offset = update["update_id"] + 1
            cq = update.get("callback_query")
            if not cq:
                continue
            data = cq.get("data", "")
            if ":" not in data:
                continue
            action, key = data.split(":", 1)
            if key not in pending:
                continue

            approved = action == "approve"
            decisions[key] = approved
            pending.discard(key)

            verdict = "✅ Approved" if approved else "❌ Skipped"
            mid = message_map.get(key)
            if mid:
                try:
                    _api(token, "editMessageText",
                         chat_id=chat_id,
                         message_id=mid,
                         text=f"{verdict}: {pieces[key]['label']}")
                except Exception:
                    pass

            try:
                _api(token, "answerCallbackQuery", callback_query_id=cq["id"])
            except Exception:
                pass

    for key in pending:
        log.warning("Approval timeout for %s — defaulting to skip", key)
        decisions[key] = False

    return decisions
