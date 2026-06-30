"""
main.py — Master Controller
Chains: Squad 1 (Intel) → Squad 2 (Content) → Squad 3 (Multimedia) → approval email
Run this daily via GitHub Actions or local cron.
"""

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from config import SQUAD_RETRY_ATTEMPTS, SQUAD_RETRY_WAIT_BASE_SECS, SQUAD_TIMEOUT_SECS

load_dotenv()

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"run_{datetime.now().strftime('%Y%m%d_%H%M')}.log"


def log(msg: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def _run_once(script_path: str, name: str) -> tuple:
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True, text=True, timeout=SQUAD_TIMEOUT_SECS,
        )
        if result.returncode == 0:
            return True, ""
        return False, f"exit code {result.returncode}: {result.stderr[-300:]}"
    except subprocess.TimeoutExpired:
        return False, f"timed out after {SQUAD_TIMEOUT_SECS}s"
    except Exception as e:
        return False, str(e)


def run_squad(script_path: str, name: str) -> bool:
    """
    Self-healing: retries a failed squad up to SQUAD_RETRY_ATTEMPTS times with
    incremental backoff before declaring it failed. Most failures in this
    pipeline are transient (LLM rate limits, flaky scraper endpoints), so a
    short retry window recovers a large fraction of runs without intervention.
    """
    log(f"Starting {name}...")
    attempts = SQUAD_RETRY_ATTEMPTS + 1
    for attempt in range(1, attempts + 1):
        ok, error = _run_once(script_path, name)
        if ok:
            if attempt > 1:
                log(f"{name} recovered on attempt {attempt}/{attempts}")
            else:
                log(f"{name} completed OK")
            return True

        log(f"{name} FAILED (attempt {attempt}/{attempts}): {error}")
        if attempt < attempts:
            wait = SQUAD_RETRY_WAIT_BASE_SECS * attempt
            log(f"Retrying {name} in {wait}s...")
            time.sleep(wait)

    log(f"{name} exhausted all {attempts} attempts — giving up.")
    return False


def send_gmail_approval(date_str: str):
    """
    Uses Gmail MCP (already connected) to send approval email to yourself.
    In practice: copy the draft from squad2_output/{date}/00_approval_email_draft.txt
    and paste into a Gmail draft, or use the Gmail MCP tool in Claude.ai directly.
    """
    draft_path = Path(f"squad2_output/{date_str}/00_approval_email_draft.txt")
    if draft_path.exists():
        log(f"Approval email draft ready at: {draft_path}")
        log("ACTION NEEDED: Open Claude.ai, use Gmail MCP to send this draft to yourself")
    else:
        log("No approval email draft found — check Squad 2 output")


def main():
    date_str = datetime.now().strftime("%Y-%m-%d")
    log("=" * 50)
    log(f"MEDIA EMPIRE DAILY RUN — {date_str}")
    log("=" * 50)

    # Step 1: Intel scrape
    squad1_ok = run_squad("squad1_intel/squad1_run.py", "Squad 1 (Intel)")
    if not squad1_ok:
        log("Squad 1 failed — aborting pipeline. Check logs.")
        sys.exit(1)

    # Step 2: Content generation
    squad2_ok = run_squad("squad2_content/squad2_run.py", "Squad 2 (Content)")
    if not squad2_ok:
        log("Squad 2 failed — Intel digest exists, content not generated today.")
        sys.exit(1)

    # Step 3: Multimedia production (TTS + metadata)
    squad3_ok = run_squad("squad3_production/squad3_run.py", "Squad 3 (Multimedia)")
    if not squad3_ok:
        log("Squad 3 failed — scripts exist but no audio/metadata generated today.")
        # Non-fatal: approval email still useful

    # Step 4: Notify for approval
    send_gmail_approval(date_str)

    log("=" * 50)
    log("DAILY RUN COMPLETE")
    log(f"Log saved: {LOG_FILE}")
    log("Next: review squad3_output/, approve scripts, then post via APIs")
    log("=" * 50)


if __name__ == "__main__":
    main()
