"""
Squad 2 — Content Creation Engine
Reads master_intel_digest.md -> generates per-niche scripts for all 7 generators
using ThreadPoolExecutor for parallel execution (max_workers=3 to respect TPM).
"""

import json
import random
import sys
import logging
import datetime as _dt
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

from config import DIGEST_PATH, OUTPUT_DIR, GROQ_MAX_TOKENS_CONTENT, SKIP_MARKERS, HOT_TAKE_PENDING_PATH, GROQ_MODEL_CONTENT
from llm import call_llm
from reports.report_card import render_report_card
import telegram_bot
from runtime_args import get_date_str

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

    Capturing stops only when a heading at the same or higher level as the
    matched heading is encountered — sub-headings (e.g. ####) inside the
    section do not end capture.
    """
    lines = digest.split("\n")
    section, capturing = [], False
    matched_level = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            if any(kw.lower() in stripped.lower() for kw in keywords):
                capturing = True
                matched_level = level
            elif capturing and level <= matched_level:
                capturing = False
        if capturing:
            section.append(line)
    return "\n".join(section).strip()


# ── Script generators ─────────────────────────────────────────────────────

AI_TECH_KEYWORDS = ["AI/Tech"]


def write_newsletter(digest: str) -> str:
    ai_tech_context = extract_niche_section(digest, AI_TECH_KEYWORDS)
    if not ai_tech_context:
        return "NO AI/TECH CONTENT TODAY"

    return call_llm(f"""
You are a sharp AI/tech newsletter editor. Write a newsletter issue based STRICTLY on the digest below.

⚠️ SOURCE LOCK: Every story, name, claim, and statistic you write MUST appear in the digest below.
Do NOT invent stories, company names, product names, or events. If the digest has 2 stories, write 2 sections — do NOT pad to 3.

AI/Tech section of today's digest (the ONLY content you may use):
{ai_tech_context}

FORMAT:
- Subject line (punchy, under 50 chars)
- Opening hook (2 sentences, conversational)
- One section per story in the digest above (headline + 2-sentence summary + "Why it matters" in 1 line)
- Closing thought (1 sentence opinion grounded in the stories above)
- CTA: "Reply and tell me which story surprised you most."

HARD RULES:
- ONLY use stories that appear verbatim in the digest above. Title-check each story against the digest.
- NEVER reference Google, Microsoft, Amazon, Meta, or any company not named in the digest.
- NEVER pull in or pivot to Cricket, Football, WWE, Movies, Gaming, or Bengali Books.
- If only 1-2 stories are in the digest, write 1-2 sections — never invent extras to fill a template.

Tone: smart friend explaining tech over coffee. Contractions OK. Not corporate.
Output ONLY the newsletter. No preamble.
""", max_tokens=GROQ_MAX_TOKENS_CONTENT, model=GROQ_MODEL_CONTENT)


_PLACEHOLDER_FRAGMENTS = ("no content today", "llm error", "no items", "_no content")

def write_twitter_thread(digest: str) -> str:
    ai_tech_context = extract_niche_section(digest, AI_TECH_KEYWORDS)
    if not ai_tech_context:
        return "NO AI/TECH CONTENT TODAY"
    # Skip if the section only contains Squad 1 placeholder text (no real stories)
    if any(p in ai_tech_context.lower() for p in _PLACEHOLDER_FRAGMENTS):
        return "NO AI/TECH CONTENT TODAY"

    return call_llm(f"""
You are a viral Twitter/X tech writer. Write a 7-tweet thread from this digest.

⚠️ SOURCE LOCK: Every factual claim in every tweet MUST trace back to a specific story in the digest below.
Do NOT invent companies, products, research outcomes, or statistics. If the digest has only 2-3 stories,
go deeper on each one (implications, context, what it means for readers) — do NOT invent new stories to fill tweets.

AI/Tech section of today's digest (the ONLY content you may use):
{ai_tech_context}

FORMAT:
Tweet 1: Hook starting with "{hook()}" — reference a REAL story from the digest above. Under 250 chars.
Tweets 2-5: Expand on the real digest stories — one angle per tweet. Under 250 chars each. Numbered (2/7), (3/7) etc.
Tweet 6: CTA — "Follow for daily AI drops" or similar, numbered (6/7)
Tweet 7: Open engagement question about the ACTUAL stories above — e.g. "Which of these caught your eye most? Drop the number 👇". Numbered (7/7). Under 200 chars.

HARD RULES:
- No hashtags (they hurt reach).
- NEVER mention Google, Microsoft, Meta, Amazon, or any company not named in the digest above.
- NEVER invent statistics, model names, product names, or research results.
- ONLY cover stories whose titles appear in the digest above.
- Each tweet must stand alone AND flow as a thread.

Output ONLY the 7 tweets. Separate each tweet with a line containing exactly three dashes on its own line:
---
No labels like "Tweet 1:" — just the tweet text, then ---, then the next tweet text.
""", max_tokens=GROQ_MAX_TOKENS_CONTENT, model=GROQ_MODEL_CONTENT)


def write_twitter_hot_take(digest: str) -> str:
    ai_tech_context = extract_niche_section(digest, AI_TECH_KEYWORDS)
    if not ai_tech_context:
        return "NO AI/TECH CONTENT TODAY"
    if any(p in ai_tech_context.lower() for p in _PLACEHOLDER_FRAGMENTS):
        return "NO AI/TECH CONTENT TODAY"

    return call_llm(f"""
You are a contrarian AI/tech commentator with strong opinions. Write ONE standalone tweet.

⚠️ SOURCE LOCK: Your opinion MUST react to a specific story named in the digest below.
Do NOT reference companies, products, or research not in the digest.

AI/Tech section of today's digest (the ONLY content you may use):
{ai_tech_context}

FORMAT:
A single punchy opinion or hot take under 240 characters. No thread numbering.
Must be opinionated — a real take reacting to the digest, not a summary. Designed to provoke replies.

Examples of the RIGHT tone (react to the real story):
- "Hot take: AI safety teams at big labs are the most expensive PR departments in history."
- "The real AI story this week isn't the benchmark. It's that nobody asked if we needed it."
- "Every 'open source' model release from a big lab is a marketing move. Fight me."

HARD RULES:
- Your take MUST be about a topic that appears in the digest above.
- NEVER reference Google, Microsoft, Meta, Amazon, OpenAI, or any entity not named in the digest.
- NEVER invent statistics or quotes.
- NO hashtags.
- Output ONLY the tweet text. No preamble, no quotes around it.
""", max_tokens=300, model=GROQ_MODEL_CONTENT)


def write_twitter_weekly_poll(digest: str) -> str:
    """Generates a poll on Mondays only; returns skip marker on other days."""
    if _dt.datetime.now().weekday() != 0:  # 0 = Monday
        return "NO POLL TODAY"

    ai_tech_context = extract_niche_section(digest, AI_TECH_KEYWORDS)
    if not ai_tech_context:
        return "NO POLL TODAY"

    raw = call_llm(f"""
You are a Twitter engagement strategist. Create a poll about this week's AI/Tech news.

AI/Tech section of today's digest:
{ai_tech_context}

OUTPUT FORMAT (JSON only, no extra text):
{{
  "question": "One punchy poll question under 200 chars",
  "options": ["Option A", "Option B", "Option C", "Option D"]
}}

Rules:
- Question must be genuinely debatable — not trivia with a correct answer.
- Each option under 25 chars.
- No hashtags.
- Output ONLY the JSON object.
""", max_tokens=200, model=GROQ_MODEL_CONTENT)

    try:
        import json as _json
        _json.loads(raw.strip())
        return raw.strip()
    except Exception:
        log.warning("Weekly poll JSON invalid — skipping: %s", raw[:100])
        return "NO POLL TODAY"


def write_reel_ai(digest: str) -> str:
    ai_tech_context = extract_niche_section(digest, AI_TECH_KEYWORDS)
    if not ai_tech_context:
        return "NO AI/TECH CONTENT TODAY"

    return call_llm(f"""
Write a 45-second Instagram Reel script for an AI/Tech account.

⚠️ SOURCE LOCK: Every sentence in this script MUST be grounded in the digest below.
Do NOT invent product names, company names, research outcomes, or statistics not in the digest.
If the digest has 2-3 academic/research stories, make them exciting to a general audience — but stay factual.

AI/Tech section of today's digest (the ONLY content you may use):
{ai_tech_context}

FORMAT:
[HOOK 0-3s]: One sentence. Start with "{hook()}". Name or reference a REAL story from the digest.
[CONTEXT 3-15s]: 2-3 sentences. What is this research/development, why does it matter now?
[THE MEAT 15-35s]: 2-3 key points from the ACTUAL digest stories. Each one punchy sentence.
[CTA 35-45s]: "Follow for daily AI news that actually matters."

HARD RULES:
- ONLY write about topics named in the AI/Tech section above.
- NEVER mention Alexa, Google Home, smart home devices, or anything not in the digest.
- NEVER invent stats, demos, or company names.
- NEVER pull in Cricket, Football, WWE, Movies, Gaming, or Bengali Books.

Tone: energetic, clear, no jargon. Spoken words, not text.
Output ONLY the script with timestamps. No preamble.
""", max_tokens=GROQ_MAX_TOKENS_CONTENT, model=GROQ_MODEL_CONTENT)


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
""", max_tokens=GROQ_MAX_TOKENS_CONTENT, model=GROQ_MODEL_CONTENT)


def write_reel_bengali(digest: str) -> str:
    book_items = [line for line in digest.split("\n")
                  if "Goodreads Bengali" in line or "Author:" in line or "Plot:" in line]
    book_context = "\n".join(book_items[:10]) if book_items else ""

    if not book_context:
        return "NO BENGALI BOOK CONTENT TODAY"

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
""", max_tokens=GROQ_MAX_TOKENS_CONTENT, model=GROQ_MODEL_CONTENT)


def write_reel_movies(digest: str) -> str:
    movies_context = extract_niche_section(digest, ["Movies", "Movies & TV", "TV"])
    if not movies_context:
        return "NO MOVIES CONTENT TODAY"

    return call_llm(f"""
Write a 45-second Reel script for a movie/series recommendation account.

⚠️ SOURCE LOCK: You MUST write about one of the specific titles named in the digest below.
Do NOT substitute a different film or series from your training knowledge — even a famous one.
The title you choose MUST appear verbatim in the digest below.

Movies & TV section of today's digest (the ONLY content you may use):
{movies_context}

FORMAT:
[HOOK 0-3s]: "{hook()}" — bold claim about ONE of the titles listed in the digest above.
[SELL IT 3-30s]: No spoilers. Sell the FEELING of that specific title. 4-5 vivid sentences.
[CREDIBILITY 30-40s]: One real fact from the digest above: director, platform, release date, or genre.
[CTA 40-45s]: "Watch it this weekend. Trust me. Follow for weekly picks."

HARD RULES:
- The film/series title you write about MUST be copied verbatim from the digest above.
- NEVER write about a title not in the digest (e.g. do not use "The Power of the Dog", "Parasite", etc.).
- NEVER invent box office numbers, critic scores, or awards not present in the digest.
- NEVER pull in AI/Tech, Gaming, Sports, or any other niche's story.
- If the section above is empty or has no real movie/TV news, output exactly: NO MOVIES CONTENT TODAY

Output ONLY the script. No preamble.
""", max_tokens=GROQ_MAX_TOKENS_CONTENT, model=GROQ_MODEL_CONTENT)


def write_reel_gaming(digest: str) -> str:
    gaming_context = extract_niche_section(digest, ["Gaming"])
    if not gaming_context:
        return "NO GAMING CONTENT TODAY"

    return call_llm(f"""
Write a 45-second Reel script for a PS5 and Steam Deck gaming account.

⚠️ SOURCE LOCK: You MUST write about one of the specific games or updates named in the digest below.
Do NOT substitute a different game title from your training knowledge.
The game title you choose MUST appear verbatim in the digest below.

Gaming section of today's digest (the ONLY content you may use):
{gaming_context}

FORMAT:
[HOOK 0-3s]: "{hook()}" — reference a REAL game/update from the digest above. Must excite a gamer.
[THE DROP 3-25s]: Explain the specific game/update from the digest in plain gamer language. Fast paced.
[VERDICT 25-38s]: Worth it or skip? Your honest take in 2 sentences, based only on what the digest says.
[CTA 38-45s]: "Follow for daily PS5 and Steam Deck drops before they sell out."

HARD RULES:
- The game title you write about MUST be copied verbatim from the digest above.
- NEVER mention Steam Deck, Portal 2, The Witcher, or any title not in the digest above.
- NEVER invent game titles, prices, release dates, or update details not in the digest.
- NEVER pull in AI/Tech, Sports, Movies, or any other niche's story.
- If the section above is empty or has no real gaming news, output exactly: NO GAMING CONTENT TODAY

Output ONLY the script. No preamble.
""", max_tokens=GROQ_MAX_TOKENS_CONTENT, model=GROQ_MODEL_CONTENT)


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

    for agent_key in ("squad2_newsletter", "squad2_twitter", "squad2_reels"):
        telegram_bot.send_agent_update(agent_key, date_str)


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    date_str = get_date_str()
    log.info("SQUAD 2: Content run — %s", date_str)

    if not DIGEST_PATH.exists():
        log.error("No digest at %s. Run Squad 1 first.", DIGEST_PATH)
        sys.exit(1)

    with open(DIGEST_PATH, "r", encoding="utf-8") as f:
        digest = f.read()

    log.info("Digest loaded. Generating scripts for all 9 generators in parallel...")

    generators = {
        "AI Newsletter":                  write_newsletter,
        "Twitter Thread (AI/Tech)":       write_twitter_thread,
        "Twitter Hot Take":               write_twitter_hot_take,
        "Twitter Weekly Poll":            write_twitter_weekly_poll,
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

    # Stage hot take for delayed posting workflow
    hot_take = scripts.get("Twitter Hot Take", "")
    if hot_take and not any(m in hot_take for m in SKIP_MARKERS):
        import json as _json
        HOT_TAKE_PENDING_PATH.write_text(
            _json.dumps({"date": date_str, "text": hot_take}, ensure_ascii=False),
            encoding="utf-8",
        )
        log.info("Hot take staged for delayed post → %s", HOT_TAKE_PENDING_PATH)

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
