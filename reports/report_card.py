"""
Shared HTML report-card renderer.
Every named agent (see config.AGENT_PROFILES) calls render_report_card() at
the end of its squad's run to produce a dark-themed per-run summary card:
a stat-box grid, a tagged item list, and a free-text note from the agent.
"""

import json
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import AGENT_PROFILES, REPORTS_DIR

CARD_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{name} — {role} — {date_str}</title>
<style>
  body {{
    background: #0d1117; color: #e6edf3; font-family: -apple-system, Segoe UI, Roboto, sans-serif;
    margin: 0; padding: 32px;
  }}
  .card {{ max-width: 640px; margin: 0 auto; background: #161b22; border: 1px solid #30363d;
    border-radius: 12px; padding: 28px; }}
  .header {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px; }}
  .agent {{ font-size: 22px; font-weight: 700; }}
  .date {{ color: #8b949e; font-size: 13px; }}
  .role {{ color: #58a6ff; font-size: 13px; margin-bottom: 20px; }}
  .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 12px; margin-bottom: 20px; }}
  .stat {{ background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 12px; text-align: center; }}
  .stat-value {{ font-size: 24px; font-weight: 700; color: #3fb950; }}
  .stat-label {{ font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.04em; margin-top: 4px; }}
  .items {{ list-style: none; padding: 0; margin: 0 0 20px 0; }}
  .items li {{ padding: 8px 0; border-bottom: 1px solid #21262d; font-size: 14px; }}
  .items li:last-child {{ border-bottom: none; }}
  .tag {{ display: inline-block; background: #1f6feb33; color: #58a6ff; border-radius: 4px;
    padding: 1px 6px; font-size: 11px; margin-right: 8px; }}
  .note {{ background: #0d1117; border-left: 3px solid #3fb950; padding: 12px 16px; font-size: 13px;
    color: #c9d1d9; line-height: 1.5; }}
</style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div class="agent">{name}</div>
      <div class="date">{date_str}</div>
    </div>
    <div class="role">{role}</div>
    <div class="stats">{stats_html}</div>
    <ul class="items">{items_html}</ul>
    <div class="note">{note_html}</div>
  </div>
</body>
</html>
"""


def render_report_card(agent_key: str, date_str: str, stats: dict, items: list, note: str) -> Path:
    """
    Render and save one HTML report card for a named agent.

    agent_key: key into config.AGENT_PROFILES (e.g. "squad1_intel")
    date_str:  "YYYY-MM-DD"
    stats:     dict of label -> value, rendered as a stat-box grid
    items:     list of {"tag": str, "text": str} rendered as a tagged list
    note:      free-text commentary from the agent

    Returns the path of the written HTML file. Also writes a JSON sidecar
    with the same data for the Chief of Staff to aggregate.
    """
    profile = AGENT_PROFILES[agent_key]
    name, role = profile["name"], profile["role"]

    stats_html = "".join(
        f'<div class="stat"><div class="stat-value">{html.escape(str(v))}</div>'
        f'<div class="stat-label">{html.escape(str(k))}</div></div>'
        for k, v in stats.items()
    )
    items_html = "".join(
        f'<li><span class="tag">{html.escape(str(i.get("tag", "")))}</span>{html.escape(str(i.get("text", "")))}</li>'
        for i in items
    ) or '<li style="color:#8b949e;">No items today.</li>'

    out = CARD_TEMPLATE.format(
        name=html.escape(name), role=html.escape(role), date_str=date_str,
        stats_html=stats_html, items_html=items_html, note_html=html.escape(note),
    )

    out_dir = REPORTS_DIR / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"{agent_key}.html"
    html_path.write_text(out, encoding="utf-8")

    json_path = out_dir / f"{agent_key}.json"
    json_path.write_text(json.dumps({
        "agent_key": agent_key, "name": name, "role": role, "date": date_str,
        "stats": stats, "items": items, "note": note,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    return html_path
