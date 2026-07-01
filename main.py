"""
main.py — Master Controller
Chains: Squad 1 (Intel) → Squad 2 (Content) → Squad 3 (Multimedia) → Squad 6
(Analytics) → Chief of Staff (Roundup) → Notify (GitHub Issue + approval
email + Telegram dashboard)
Run this daily via GitHub Actions or local cron.
"""

import subprocess
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

import notify
from config import LOG_DIR, SQUAD_RETRY_ATTEMPTS, SQUAD_RETRY_WAIT_BASE_SECS, SQUAD_TIMEOUT_SECS

load_dotenv()

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

    # Step 4: Publishing — Telegram approval then Twitter posting
    squad4_ok = run_squad("squad4_publish/squad4_run.py", "Squad 4 (Publishing)")
    if not squad4_ok:
        log("Squad 4 failed — scripts exist but nothing posted to Twitter today.")
        # Non-fatal: rest of pipeline continues

    # Step 5: Analytics feedback loop (updates niche_boosts.json for tomorrow's Squad 1)
    run_squad("squad6_analytics/analytics_run.py", "Squad 6 (Analytics)")

    # Step 6: Chief of Staff rounds up every agent's report card for today
    run_squad("chief_of_staff.py", "Chief of Staff (Roundup)")

    # Step 7: Notify — GitHub Issue roundup + approval email (each optional, best-effort)
    notify.notify_all(date_str)

    log("=" * 50)
    log("DAILY RUN COMPLETE")
    log(f"Log saved: {LOG_FILE}")
    log("Next: review squad3_output/, approve scripts, then post via APIs")
    log("=" * 50)


if __name__ == "__main__":
    main()
