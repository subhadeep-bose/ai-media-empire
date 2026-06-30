"""
Squad 2 — Content Creation Engine
Reads master_intel_digest.md -> generates per-niche scripts for all 7 generators
using ThreadPoolExecutor for parallel execution (max_workers=3 to respect TPM).
"""

import json
import random
import sys
import logging
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add repo root to sys.path so config/llm imports work
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
log = logging.getLogger(__name__)

from config import DIGEST_PATH, OUTPUT_DIR, GROQ_MAX_TOKENS_CONTENT, SKIP_MARKERS
from llm import call_llm
from reports.report_card import render_report_card

OUTPUT_DIR.mkdir(exist_ok=True)


# ── Hook variation (shadowban protection) ─────────────────────────────────

HOOK_STARTERS = [
    "Nobody is talking about",
    "This just changed everything about",
    "The internet is sleeping on",
    "Stop scrolling — you need to know about",
    "Here's what most people miss about",
    "Hot take:",
    "This week's most underrated story:",
    "I had to share this:",
]

def hook() -> str:
    return random.choice(HOOK_STARTERS)


# ── Niche section extraction (prevents cross-niche content bleed) ─────────

def extract_niche_section(digest: str, keywords: list) -> str:
    """
    Return only the markdown section(s) whose header line matches one of the
    given keywords (case-insensitive). Prevents a generator from grabbing an
    unrelated story (e.g. AI/Tech) when its own niche has no real content.
    """
    lines = digest.split("\n")
    section, capturing = [], False
    for line in lines:
        if line.strip().startswith("#"):
            capturing = any(kw.lower() in line.lower() for kw in keywords)
        if capturing:
            section.append(line)
    return "\n".join(section).strip()


# ── Script generators ─────────────────────────────────────────────────────

def write_newsletter(digest: str) -> str:
    return call_llm(f"""
You are a sharp AI/tech newsletter editor. Write a weekly newsletter issue.

Source digest:
{digest}

FORMAT:
- Subject line (punchy, under 50 chars)
- Opening hook (2 sentences, conversational)
- 3 main stories with headline, 2-sentence summary, and "Why it matters" in 1 line each
- Closing thought (1 sentence opinion)
- CTA: "Reply and tell me which story surprised you most."

Tone: smart friend explaining tech over coffee. Contractions OK. Not corporate.
Output ONLY the newsletter. No preamble.
""", max_tokens=GROQ_MAX_TOKENS_CONTENT)


def write_twitter_thread(digest: str) -> str:
    return call_llm(f"""
You are a viral Twitter/X tech writer. Write a 6-tweet thread from this digest.

Source digest:
{digest}

FORMAT:
Tweet 1: Hook starting with "{hook()}" — must create curiosity gap, under 250 chars
Tweets 2-5: One insight each, under 250 chars, numbered (2/6), (3/6) etc.
Tweet 6: CTA — "Follow for daily AI drops" or similar

Rules:
- No hashtags (they hurt reach).
- Each tweet must stand alone AND flow as a thread.
- NEVER invent statistics, numbers, or data not present in the source digest.
- Only use facts directly from the digest — no embellishment.
Output ONLY the tweets separated by ---
""", max_tokens=GROQ_MAX_TOKENS_CONTENT)


def write_reel_ai(digest: str) -> str:
    return call_llm(f"""
Write a 45-second Instagram Reel script for an AI/Tech account.

Source digest:
{digest}

FORMAT:
[HOOK 0-3s]: One sentence. Start with "{hook()}". Stop-scroll energy.
[CONTEXT 3-15s]: 2-3 sentences. What is this, why now?
[THE MEAT 15-35s]: 3 key points, each one punchy sentence.
[CTA 35-45s]: "Follow for daily AI news that actually matters."

Tone: energetic, clear, no jargon. Spoken words, not text.
Output ONLY the script with timestamps. No preamble.
""", max_tokens=GROQ_MAX_TOKENS_CONTENT)


def write_reel_sports(digest: str) -> str:
    sports_context = extract_niche_section(digest, ["Cricket", "Football", "WWE"])
    if not sports_context:
        return "NO SPORTS CONTENT TODAY"

    return call_llm(f"""
Write a 45-second Reel script for a Cricket, Football and WWE sports account.

Sports section of today's digest (the ONLY content you may use):
{sports_context}

FORMAT:
[HOOK 0-3s]: "{hook()}" - pure emotion. Betrayal, shock, history being made.
[THE STORY 3-30s]: Tell it fast. Vivid. 4-5 punchy sentences.
[REACTION 30-40s]: What fans are saying - based ONLY on what the digest mentions.
[CTA 40-45s]: "Follow for daily sports takes you won't see on TV."

CRITICAL RULES - breaking these destroys credibility:
- ONLY use facts, names, scores that appear in the sports section above.
- NEVER pull in or pivot to AI/Tech, Gaming, Movies, or any other niche's story.
- NEVER invent match results, scores, player statistics, or player quotes.
- NEVER fabricate a quote from any real person.
- If the sports section above is empty or has no real news, output exactly: NO SPORTS CONTENT TODAY
- NEVER include hashtags anywhere in the output.

Tone: match-day energy. Short sentences. Drama only for real events.
Output ONLY the script. No preamble.
""", max_tokens=GROQ_MAX_TOKENS_CONTENT)


def write_reel_bengali(digest: str) -> str:
    book_items = [line for line in digest.split("\n")
                  if "Goodreads Bengali" in line or "Author:" in line or "Plot:" in line]
    book_context = "\n".join(book_items[:10]) if book_items else ""

    return call_llm(f"""
Write a 45-second Reel script reviewing a Bengali book for Instagram/Shorts.

Source digest:
{digest}

Extracted book facts (use ONLY these):
{book_context}

FORMAT:
[HOOK 0-3s]: Start with the book title in Bengali script (from digest). Then: "If you haven't read this, you're missing one of the greatest stories ever written."
[ABOUT 3-20s]: Author name (from digest only), genre (from digest only), one-line plot (from digest only).
[WHY READ 20-38s]: 2-3 emotional reasons based on the actual plot described in the digest.
[CTA 38-45s]: "Link to buy in bio. Bengali literature is criminally underrated worldwide."

CRITICAL RULES:
- Use ONLY the author name and plot from the digest above. Never substitute a different author.
- If plot details are unavailable in the digest, say "one of the most beloved stories in Bengali literature" — do not invent plot details.
- If no Bengali book is in the digest, output exactly: NO BENGALI BOOK CONTENT TODAY
- Language: English with Bengali titles in native script.

Output ONLY the script. No preamble.
""", max_tokens=GROQ_MAX_TOKENS_CONTENT)


def write_reel_movies(digest: str) -> str:
    movies_context = extract_niche_section(digest, ["Movies", "Movies & TV", "TV"])
    if not movies_context:
        return "NO MOVIES CONTENT TODAY"

    return call_llm(f"""
Write a 45-second Reel script for a movie/series recommendation account.

Movies & TV section of today's digest (the ONLY content you may use):
{movies_context}

FORMAT:
[HOOK 0-3s]: "{hook()}" — bold claim about this film/series.
[SELL IT 3-30s]: No spoilers. Sell the FEELING, not the plot. 4-5 vivid sentences.
[CREDIBILITY 30-40s]: One real fact from the section above: box office, critic score, director, or award.
[CTA 40-45s]: "Watch it this weekend. Trust me. Follow for weekly picks."

CRITICAL RULES:
- ONLY write about the film/series named in the section above.
- NEVER pull in or pivot to AI/Tech, Gaming, Sports, or any other niche's story.
- NEVER invent box office numbers, critic scores, or awards not present above.
- If the section above is empty or has no real movie/TV news, output exactly: NO MOVIES CONTENT TODAY

Output ONLY the script. No preamble.
""", max_tokens=GROQ_MAX_TOKENS_CONTENT)


def write_reel_gaming(digest: str) -> str:
    gaming_context = extract_niche_section(digest, ["Gaming"])
    if not gaming_context:
        return "NO GAMING CONTENT TODAY"

    return call_llm(f"""
Write a 45-second Reel script for a PS5 and Steam Deck gaming account.

Gaming section of today's digest (the ONLY content you may use):
{gaming_context}

FORMAT:
[HOOK 0-3s]: "{hook()}" — must excite a gamer immediately.
[THE DROP 3-25s]: Explain the game/update/deal in plain gamer language. Fast paced.
[VERDICT 25-38s]: Worth it or skip? Your honest take in 2 sentences.
[CTA 38-45s]: "Follow for daily PS5 and Steam Deck drops before they sell out."

CRITICAL RULES:
- ONLY write about gaming topics in the section above (PS5, Steam Deck, PC gaming, game releases, deals, updates).
- NEVER pull in or pivot to AI/Tech, Sports, Movies, or any other niche's story.
- If the section above is empty or has no real gaming news, output exactly: NO GAMING CONTENT TODAY
- NEVER invent game titles, prices, or release dates not in the section above.

Output ONLY the script. No preamble.
""", max_tokens=GROQ_MAX_TOKENS_CONTENT)


# ── Approval email ─────────────────────────────────────────────────────────

def build_approval_email(scripts: dict, date_str: str) -> str:
    lines = [f"Subject: [Media Empire] Approve today's content — {date_str}\n"]
    lines.append("Reply APPROVE, EDIT, or SKIP for each piece.\n")
    lines.append("=" * 50)
    for name, content in scripts.items():
        preview = content[:500] + "..." if len(content) > 500 else content
        lines.append(f"\n## {name}\n")
        lines.append(preview)
        lines.append("\n[ ] APPROVE  [ ] EDIT  [ ] SKIP")
        lines.append("-" * 40)
    return "\n".join(lines)


# ── Report cards ────────────────────────────────────────────────────────────

REEL_NAMES = {
    "Instagram Reel (AI/Tech)", "Instagram Reel (Sports)", "Instagram Reel (Bengali Books)",
    "Instagram Reel (Movies)", "Instagram Reel (Gaming)",
}


def _script_status(content: str) -> str:
    if content.startswith("[ERROR]"):
        return "error"
    if any(marker in content for marker in SKIP_MARKERS):
        return "skipped"
    return "ok"


def render_squad2_report_cards(scripts: dict, date_str: str) -> None:
    newsletter = scripts.get("AI Newsletter", "")
    render_report_card(
        "squad2_newsletter", date_str,
        stats={"Chars Written": len(newsletter), "Status": _script_status(newsletter)},
        items=[{"tag": "newsletter", "text": newsletter[:120]}] if newsletter else [],
        note="Weekly AI/tech newsletter issue drafted and ready for approval."
             if _script_status(newsletter) == "ok" else "Newsletter generation hit an issue this run.",
    )

    thread = scripts.get("Twitter Thread (AI/Tech)", "")
    render_report_card(
        "squad2_twitter", date_str,
        stats={"Chars Written": len(thread), "Status": _script_status(thread)},
        items=[{"tag": "thread", "text": thread[:120]}] if thread else [],
        note="6-tweet thread drafted from today's digest."
             if _script_status(thread) == "ok" else "Twitter thread generation hit an issue this run.",
    )

    reel_items = [{"tag": name.replace("Instagram Reel (", "").rstrip(")"),
                   "text": f"{_script_status(content)} — {len(content)} chars"}
                  for name, content in scripts.items() if name in REEL_NAMES]
    ok_count = sum(1 for name, content in scripts.items()
                   if name in REEL_NAMES and _script_status(content) == "ok")
    skip_count = sum(1 for name, content in scripts.items()
                      if name in REEL_NAMES and _script_status(content) == "skipped")
    render_report_card(
        "squad2_reels", date_str,
        stats={"Reels Written": ok_count, "Skipped (no data)": skip_count, "Niches Covered": len(REEL_NAMES)},
        items=reel_items,
        note=f"{ok_count}/{len(REEL_NAMES)} Reel scripts ready across AI/Tech, Sports, "
             f"Bengali Books, Movies and Gaming.",
    )


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    date_str = datetime.now().strftime("%Y-%m-%d")
    log.info("SQUAD 2: Content run — %s", date_str)

    if not DIGEST_PATH.exists():
        log.error("No digest at %s. Run Squad 1 first.", DIGEST_PATH)
        sys.exit(1)

    with open(DIGEST_PATH, "r", encoding="utf-8") as f:
        digest = f.read()

    log.info("Digest loaded. Generating scripts for all 7 generators in parallel...")

    generators = {
        "AI Newsletter":                  write_newsletter,
        "Twitter Thread (AI/Tech)":       write_twitter_thread,
        "Instagram Reel (AI/Tech)":       write_reel_ai,
        "Instagram Reel (Sports)":        write_reel_sports,
        "Instagram Reel (Bengali Books)": write_reel_bengali,
        "Instagram Reel (Movies)":        write_reel_movies,
        "Instagram Reel (Gaming)":        write_reel_gaming,
    }

    scripts = {}
    futures_map = {}

    with ThreadPoolExecutor(max_workers=3) as executor:
        for name, fn in generators.items():
            future = executor.submit(fn, digest)
            futures_map[future] = name

        for future in as_completed(futures_map):
            name = futures_map[future]
            try:
                result = future.result()
            except Exception as e:
                log.exception("Generator %s raised an exception", name)
                result = f"[ERROR] Generator exception: {e}"
            scripts[name] = result
            if result.startswith("[ERROR]"):
                log.warning("[%s] %s", name, result)
            else:
                log.info("[%s] done (%d chars)", name, len(result))

    error_count = sum(1 for v in scripts.values() if v.startswith("[ERROR]"))
    if error_count > 3:
        log.error("%d generators failed (threshold: 3). Exiting with code 1.", error_count)
        sys.exit(1)

    render_squad2_report_cards(scripts, date_str)

    # Save individual files
    scripts_dir = OUTPUT_DIR / date_str
    scripts_dir.mkdir(parents=True, exist_ok=True)

    for name, content in scripts.items():
        safe = name.lower().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")
        with open(scripts_dir / f"{safe}.txt", "w", encoding="utf-8") as f:
            f.write(content)

    # Approval email
    email_draft = build_approval_email(scripts, date_str)
    with open(scripts_dir / "00_approval_email_draft.txt", "w", encoding="utf-8") as f:
        f.write(email_draft)

    # Full bundle
    with open(OUTPUT_DIR / f"bundle_{date_str}.json", "w", encoding="utf-8") as f:
        json.dump({"date": date_str, "scripts": scripts}, f, indent=2, ensure_ascii=False)

    log.info("%d scripts saved to %s", len(scripts), scripts_dir)
    log.info("Approval email: %s/00_approval_email_draft.txt", scripts_dir)
    preview = scripts.get("AI Newsletter", "")[:400]
    log.info("NEWSLETTER PREVIEW: %s ...", preview)


if __name__ == "__main__":
    main()
