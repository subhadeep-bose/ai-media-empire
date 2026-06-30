"""
Notify — surfaces the Chief of Staff's daily roundup outside the Actions
artifact: opens/updates a GitHub Issue and emails the approval draft.
Both channels are best-effort and independently optional — missing
credentials for one don't block the other, they just log a warning and
skip. Safe to run standalone (CI) or imported from main.py (local/cron).
"""

import json
import logging
import smtplib
import sys
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))

from config import (
    REPORTS_DIR, OUTPUT_DIR, GITHUB_REPOSITORY, GITHUB_TOKEN, ROUNDUP_ISSUE_LABEL,
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, NOTIFY_EMAIL_TO,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("notify")

GITHUB_API = "https://api.github.com"


def load_roundup(date_str: str) -> dict:
    path = REPORTS_DIR / date_str / "chief_of_staff.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_summary(date_str: str, roundup: dict) -> str:
    if not roundup:
        return f"No Chief of Staff roundup found for {date_str} — squads may not have run yet."
    lines = [roundup.get("note", ""), ""]
    for item in roundup.get("items", []):
        lines.append(f"- {item.get('tag', '')}: {item.get('text', '')}")
    return "\n".join(lines)


def post_github_issue(date_str: str, summary: str, run_id: str = "") -> None:
    if not GITHUB_TOKEN or not GITHUB_REPOSITORY:
        log.warning("GITHUB_TOKEN/GITHUB_REPOSITORY not set — skipping GitHub Issue notification")
        return

    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    title = f"Daily roundup — {date_str}"
    run_url = f"https://github.com/{GITHUB_REPOSITORY}/actions/runs/{run_id}" if run_id else ""
    body = summary + (f"\n\nRun: {run_url}" if run_url else "")

    try:
        resp = requests.get(
            f"{GITHUB_API}/repos/{GITHUB_REPOSITORY}/issues",
            headers=headers, params={"labels": ROUNDUP_ISSUE_LABEL, "state": "open"}, timeout=10,
        )
        resp.raise_for_status()
        existing = next((i for i in resp.json() if i["title"] == title), None)

        if existing:
            requests.post(
                f"{GITHUB_API}/repos/{GITHUB_REPOSITORY}/issues/{existing['number']}/comments",
                headers=headers, json={"body": body}, timeout=10,
            ).raise_for_status()
            log.info("Updated existing roundup issue #%d", existing["number"])
        else:
            resp = requests.post(
                f"{GITHUB_API}/repos/{GITHUB_REPOSITORY}/issues",
                headers=headers, json={"title": title, "body": body, "labels": [ROUNDUP_ISSUE_LABEL]},
                timeout=10,
            )
            resp.raise_for_status()
            log.info("Opened roundup issue #%d", resp.json()["number"])
    except requests.RequestException:
        log.exception("Failed to post GitHub Issue notification")


def send_approval_email(date_str: str, summary: str) -> None:
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD, NOTIFY_EMAIL_TO]):
        log.warning("SMTP_* / NOTIFY_EMAIL_TO not fully set — skipping approval email")
        return

    draft_path = OUTPUT_DIR / date_str / "00_approval_email_draft.txt"
    draft = draft_path.read_text(encoding="utf-8") if draft_path.exists() else "(no approval draft found)"

    body = f"{summary}\n\n{'=' * 50}\n\n{draft}"
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"[Media Empire] Daily roundup & approval — {date_str}"
    msg["From"] = SMTP_USER
    msg["To"] = NOTIFY_EMAIL_TO

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        log.info("Approval email sent to %s", NOTIFY_EMAIL_TO)
    except (smtplib.SMTPException, OSError):
        log.exception("Failed to send approval email")


def notify_all(date_str: str, run_id: str = "") -> None:
    roundup = load_roundup(date_str)
    summary = build_summary(date_str, roundup)
    post_github_issue(date_str, summary, run_id)
    send_approval_email(date_str, summary)


def main():
    import os
    date_str = datetime.now().strftime("%Y-%m-%d")
    notify_all(date_str, run_id=os.getenv("GITHUB_RUN_ID", ""))


if __name__ == "__main__":
    main()
