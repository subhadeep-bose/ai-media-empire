"""
Dashboard — builds a richer, stat-tile HTML snapshot of the day's full run
(all squads + Chief of Staff) and renders it to a PNG via headless Chromium
(Playwright) for delivery to Telegram alongside the existing GitHub Issue
and approval email channels.

PNG rendering is best-effort: if Playwright/Chromium isn't available, this
logs a warning and returns None rather than failing the pipeline — the
text-only Telegram summary still goes out.
"""

import html
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import AGENT_PROFILES, REPORTS_DIR
from chief_of_staff import AGENT_RUN_ORDER, load_agent_reports
from reports.png_render import render_html_to_png

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("dashboard")

DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Daily Intel Sweep — {date_str}</title>
<style>
  body {{
    background: #0d1117; color: #e6edf3; font-family: -apple-system, Segoe UI, Roboto, sans-serif;
    margin: 0; padding: 32px;
  }}
  .dashboard {{ max-width: 760px; margin: 0 auto; background: #161b22; border: 1px solid #30363d;
    border-radius: 12px; padding: 28px; }}
  .header {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 20px; }}
  .title {{ font-size: 24px; font-weight: 700; }}
  .date {{ color: #8b949e; font-size: 13px; }}
  .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 12px; margin-bottom: 24px; }}
  .stat {{ background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 14px; text-align: center; }}
  .stat-value {{ font-size: 26px; font-weight: 700; color: #3fb950; }}
  .stat-label {{ font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.04em; margin-top: 4px; }}
  .section-title {{ font-size: 13px; color: #58a6ff; text-transform: uppercase; letter-spacing: 0.04em;
    margin: 24px 0 10px 0; }}
  .breakdown {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }}
  .squad-card {{ background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 12px 14px; }}
  .squad-name {{ font-weight: 700; font-size: 14px; }}
  .squad-role {{ color: #8b949e; font-size: 11px; margin-bottom: 6px; }}
  .squad-note {{ color: #c9d1d9; font-size: 12px; line-height: 1.4; }}
  .items {{ list-style: none; padding: 0; margin: 0; }}
  .items li {{ padding: 8px 0; border-bottom: 1px solid #21262d; font-size: 14px; }}
  .items li:last-child {{ border-bottom: none; }}
  .tag {{ display: inline-block; background: #1f6feb33; color: #58a6ff; border-radius: 4px;
    padding: 1px 6px; font-size: 11px; margin-right: 8px; }}
</style>
</head>
<body>
  <div class="dashboard">
    <div class="header">
      <div class="title">Daily Intel Sweep</div>
      <div class="date">{date_str}</div>
    </div>
    <div class="stats">{stats_html}</div>
    <div class="section-title">Breakdown by Squad</div>
    <div class="breakdown">{breakdown_html}</div>
    <div class="section-title">Top Items</div>
    <ul class="items">{items_html}</ul>
  </div>
</body>
</html>
"""


def _overall_stats(reports: dict) -> dict:
    stats = {"Agents Reported": len(reports), "Agents Tracked": len(AGENT_RUN_ORDER)}
    intel = reports.get("squad1_intel", {}).get("stats", {})
    if "Items Collected" in intel:
        stats["Items Collected"] = intel["Items Collected"]
    if "Boosted Niches" in intel:
        stats["Boosted Niches"] = intel["Boosted Niches"]
    reels = reports.get("squad2_reels", {}).get("stats", {})
    if "Reels Written" in reels:
        stats["Reels Written"] = reels["Reels Written"]
    production = reports.get("squad3_production", {}).get("stats", {})
    if "Audio" in production:
        stats["Audio Produced"] = production["Audio"]
    if "Video" in production:
        stats["Video Produced"] = production["Video"]
    return stats


def build_dashboard_html(date_str: str, reports: dict) -> str:
    stats = _overall_stats(reports)
    stats_html = "".join(
        f'<div class="stat"><div class="stat-value">{html.escape(str(v))}</div>'
        f'<div class="stat-label">{html.escape(str(k))}</div></div>'
        for k, v in stats.items()
    )

    breakdown_html = "".join(
        f'<div class="squad-card">'
        f'<div class="squad-name">{html.escape(AGENT_PROFILES[key]["name"])}</div>'
        f'<div class="squad-role">{html.escape(AGENT_PROFILES[key]["role"])}</div>'
        f'<div class="squad-note">{html.escape(data.get("note", ""))}</div>'
        f'</div>'
        for key, data in reports.items()
    ) or '<div class="squad-card squad-note">No agents reported today.</div>'

    top_items = []
    for key in AGENT_RUN_ORDER:
        data = reports.get(key)
        if not data:
            continue
        for item in data.get("items", [])[:3]:
            top_items.append(item)
    items_html = "".join(
        f'<li><span class="tag">{html.escape(str(i.get("tag", "")))}</span>{html.escape(str(i.get("text", "")))}</li>'
        for i in top_items[:15]
    ) or '<li style="color:#8b949e;">No items today.</li>'

    return DASHBOARD_TEMPLATE.format(
        date_str=date_str, stats_html=stats_html,
        breakdown_html=breakdown_html, items_html=items_html,
    )


def render_dashboard_png(html_path: Path, png_path: Path) -> Path | None:
    """
    Renders the dashboard HTML to a PNG via headless Chromium. Returns the
    PNG path on success, or None if Playwright/Chromium isn't available —
    this must never raise, so the pipeline can keep going with a text-only
    Telegram summary instead.
    """
    return render_html_to_png(html_path, png_path)


def build_dashboard(date_str: str) -> tuple[Path, Path | None]:
    reports = load_agent_reports(date_str)
    out_dir = REPORTS_DIR / date_str
    out_dir.mkdir(parents=True, exist_ok=True)

    html_out = build_dashboard_html(date_str, reports)
    html_path = out_dir / "dashboard.html"
    html_path.write_text(html_out, encoding="utf-8")

    png_path = render_dashboard_png(html_path, out_dir / "dashboard.png")
    return html_path, png_path


def main():
    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d")
    html_path, png_path = build_dashboard(date_str)
    log.info("Dashboard HTML saved to %s", html_path)
    if png_path:
        log.info("Dashboard PNG saved to %s", png_path)
    else:
        log.warning("Dashboard PNG not generated this run")


if __name__ == "__main__":
    main()
