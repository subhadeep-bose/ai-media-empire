"""
Chief of Staff — aggregates today's per-agent report cards (squad1_intel,
squad2_newsletter, squad2_twitter, squad2_reels, squad3_production,
squad6_analytics) into a single daily overview card.

Run after all squads have produced their reports/<date>/<agent_key>.json
sidecar files (see reports/report_card.py).
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import AGENT_PROFILES, REPORTS_DIR
from reports.report_card import render_report_card
import telegram_bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("chief_of_staff")

AGENT_RUN_ORDER = [
    "squad1_intel", "squad2_newsletter", "squad2_twitter", "squad2_reels",
    "squad3_production", "squad6_analytics",
]


def load_agent_reports(date_str: str) -> dict:
    out_dir = REPORTS_DIR / date_str
    reports = {}
    for agent_key in AGENT_RUN_ORDER:
        path = out_dir / f"{agent_key}.json"
        if path.exists():
            reports[agent_key] = json.loads(path.read_text(encoding="utf-8"))
    return reports


def main():
    date_str = datetime.now().strftime("%Y-%m-%d")
    log.info("CHIEF OF STAFF: daily roundup — %s", date_str)

    reports = load_agent_reports(date_str)
    reported = list(reports.keys())
    missing = [k for k in AGENT_RUN_ORDER if k not in reports]

    items = [
        {"tag": AGENT_PROFILES[key]["name"], "text": data.get("note", "")}
        for key, data in reports.items()
    ]
    for key in missing:
        items.append({"tag": AGENT_PROFILES[key]["name"], "text": "no report filed today"})

    render_report_card(
        "chief_of_staff", date_str,
        stats={"Agents Reported": len(reported), "Agents Missing": len(missing)},
        items=items,
        note=f"Daily run complete. {len(reported)}/{len(AGENT_RUN_ORDER)} agents filed a report."
             + (f" Missing: {', '.join(AGENT_PROFILES[k]['name'] for k in missing)}." if missing else ""),
    )
    telegram_bot.send_agent_update("chief_of_staff", date_str)

    log.info("%d/%d agents reported in. Roundup saved to %s",
              len(reported), len(AGENT_RUN_ORDER), REPORTS_DIR / date_str / "chief_of_staff.html")


if __name__ == "__main__":
    main()
