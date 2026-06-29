"""
Squad 2 — Content Creation Engine
Reads master_intel_digest.md → generates per-niche scripts for all 5 accounts.
Outputs: newsletter draft, Twitter threads, Instagram Reel scripts, book reviews, movie hooks.
Each output gets a randomised phrasing variant to avoid platform shadowban detection.
"""

import os
import json
import random
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).parent.parent
load_dotenv(REPO_ROOT / ".env")

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DIGEST_PATH = REPO_ROOT / "master_intel_digest.md"
OUTPUT_DIR = REPO_ROOT / "squad2_output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ── LLM caller (same Ollama + Groq fallback pattern) ──────────────────────

def call_llm(prompt: str) -> str:
    try:
        import ollama
        r = ollama.chat(model=OLLAMA_MODEL, messages=[{"role": "user", "content": prompt}])
        return r["message"]["content"]
    except Exception:
        if not GROQ_API_KEY:
            return "[ERROR] No LLM available"
        try:
            import requests
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": prompt}], "max_tokens": 1500},
                timeout=60,
            )
            data = r.json()
            if "choices" not in data:
                return f"[ERROR] Groq API error: {data.get('error', data)}"
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[ERROR] {e}"


# ── Phrasing variant randomiser (shadowban protection) ────────────────────

HOOK_STARTERS = [
    "Nobody is talking about",
    "This just changed everything about",
    "I had to share this about",
    "The internet is sleeping on",
    "Stop scrolling — you need to know about",
    "Hot take on",
    "Here's what most people miss about",
    "This week's most underrated story:",
]

def random_hook_prefix() -> str:
    return random.choice(HOOK_STARTERS)


# ── Per-niche content generators ──────────────────────────────────────────

def write_newsletter(digest: str) -> str:
    prompt = f"""
You are a sharp AI/tech newsletter editor. Write a weekly newsletter issue.

Source digest:
{digest}

FORMAT:
- Subject line (punchy, under 50 chars)
- Opening hook (2 sentences, conversational)
- 3 main stories — each with a headline, 2-sentence summary, and "Why it matters" in 1 line
- Closing thought (1 sentence opinion)
- Call to action: "Reply and tell me which story surprised you most."

Tone: smart friend explaining tech over coffee. Not corporate. Contractions OK.
Output ONLY the newsletter content. No preamble.
"""
    return call_llm(prompt)


def write_twitter_thread(digest: str) -> str:
    prompt = f"""
You are a viral Twitter/X tech writer. Write a 6-tweet thread from this digest.

Source digest:
{digest}

FORMAT:
Tweet 1: Hook — start with "{random_hook_prefix()}" — must create curiosity gap
Tweets 2–5: One insight per tweet. Under 250 chars each. Punchy. Numbered (2/6), (3/6) etc.
Tweet 6: CTA — "Follow for daily AI drops" or similar

Rules:
- No hashtags (they kill reach in 2024+)
- Each tweet must stand alone AND flow as a thread
- Start Tweet 1 with a number or surprising stat if possible
Output ONLY the tweets, one per line, separated by ---
"""
    return call_llm(prompt)


def write_reel_script_ai(digest: str) -> str:
    prompt = f"""
You are a viral short-form video scriptwriter for an AI/Tech Instagram account.
Write ONE 45-second Reel script from the most interesting AI story in this digest.

Source digest:
{digest}

FORMAT:
[HOOK - 0-3s]: One sentence. Start with "{random_hook_prefix()}". Must stop the scroll.
[CONTEXT - 3-15s]: 2-3 sentences. What is this? Why now?
[THE MEAT - 15-35s]: 3 key points, each one punchy sentence.
[CTA - 35-45s]: "Follow for daily AI news that actually matters" or variant.

Tone: energetic, clear, no jargon. Written as SPOKEN words, not text.
Output ONLY the script with the timestamps. No preamble.
"""
    return call_llm(prompt)


def write_reel_script_sports(digest: str) -> str:
    prompt = f"""
You are a viral sports short-form scriptwriter covering Cricket, Football, and WWE.
Write ONE 45-second Reel script from the hottest sports story in this digest.

Source digest:
{digest}

FORMAT:
[HOOK - 0-3s]: "{random_hook_prefix()}" — pure emotion. Betrayal, shock, history.
[THE STORY - 3-30s]: Tell it fast. Vivid. 4–5 punchy sentences.
[REACTION - 30-40s]: What are fans saying? One contrasting view.
[CTA - 40-45s]: "Follow for daily sports takes you won't see on TV."

Tone: match-day energy. Short sentences. Drama allowed.
Output ONLY the script. No preamble.
"""
    return call_llm(prompt)


def write_bengali_book_review(digest: str) -> str:
    prompt = f"""
You are a Bengali literature reviewer writing for Instagram Reels and Shorts.
Write ONE 45-second Reel script reviewing the Bengali book from this digest.

Source digest:
{digest}

FORMAT:
[HOOK - 0-3s]: Start with the book's Bengali title in native script (e.g. চাঁদের পাহাড়).
              Then: "If you haven't read this, you're missing one of the greatest stories ever written."
[ABOUT - 3-20s]: Author, genre, one-line plot. Keep it accessible to non-Bengali viewers too.
[WHY READ - 20-38s]: 2–3 emotional reasons. What will the reader FEEL?
[CTA - 38-45s]: "Link to buy in bio. Bengali literature is criminally underrated worldwide."

Language: English with Bengali titles/names in native script.
Output ONLY the script. No preamble.
"""
    return call_llm(prompt)


def write_movie_hook(digest: str) -> str:
    prompt = f"""
You are a film critic writing viral movie/series recommendation scripts for Reels.
Write ONE 45-second Reel script from the most interesting movie story in this digest.

Source digest:
{digest}

FORMAT:
[HOOK - 0-3s]: "{random_hook_prefix()}" — bold claim about this film/series.
[SELL IT - 3-30s]: No spoilers. Sell the FEELING, not the plot. 4–5 vivid sentences.
[CREDIBILITY - 30-40s]: One real fact: box office, critic score, director, award.
[CTA - 40-45s]: "Watch it this weekend. Trust me. Follow for weekly picks."

Output ONLY the script. No preamble.
"""
    return call_llm(prompt)


def write_gaming_script(digest: str) -> str:
    prompt = f"""
You are a PS5 and Steam Deck content creator writing viral gaming Reels.
Write ONE 45-second Reel script from the most interesting gaming story in this digest.

Source digest:
{digest}

FORMAT:
[HOOK - 0-3s]: "{random_hook_prefix()}" — must excite a gamer immediately.
[THE DROP - 3-25s]: Explain the game/update/deal in plain gamer language. Fast paced.
[VERDICT - 25-38s]: Worth it or skip? Your honest take in 2 sentences.
[CTA - 38-45s]: "Follow for daily PS5 and Steam Deck deals before they sell out."

Output ONLY the script. No preamble.
"""
    return call_llm(prompt)


# ── Email approval draft (Gmail MCP hook) ─────────────────────────────────

def build_approval_email(scripts: dict, date_str: str) -> str:
    lines = [f"Subject: [Media Empire] Content approval needed — {date_str}\n"]
    lines.append("Here are today's generated scripts. Reply APPROVE, EDIT, or SKIP for each.\n")
    lines.append("=" * 50)
    for name, content in scripts.items():
        lines.append(f"\n## {name}\n")
        lines.append(content[:600] + "...\n" if len(content) > 600 else content)
        lines.append("\n[ ] APPROVE  [ ] EDIT  [ ] SKIP")
        lines.append("-" * 40)
    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    date_str = datetime.now().strftime("%Y-%m-%d")
    print(f"\n{'='*55}")
    print(f"  SQUAD 2: Content run — {date_str}")
    print(f"{'='*55}")

    if not DIGEST_PATH.exists():
        print(f"[ERROR] No digest found at {DIGEST_PATH}. Run Squad 1 first.")
        return

    with open(DIGEST_PATH, "r", encoding="utf-8") as f:
        digest = f.read()

    print("[INFO] Digest loaded. Generating scripts for all 5 accounts...")

    scripts = {}

    print("  [1/7] Newsletter...")
    scripts["AI Newsletter"] = write_newsletter(digest)

    print("  [2/7] Twitter/X thread...")
    scripts["Twitter Thread (AI/Tech)"] = write_twitter_thread(digest)

    print("  [3/7] Instagram Reel — AI/Tech account...")
    scripts["Instagram Reel (AI/Tech)"] = write_reel_script_ai(digest)

    print("  [4/7] Instagram Reel — Sports account...")
    scripts["Instagram Reel (Sports)"] = write_reel_script_sports(digest)

    print("  [5/7] Instagram Reel — Bengali Books account...")
    scripts["Instagram Reel (Bengali Books)"] = write_bengali_book_review(digest)

    print("  [6/7] Instagram Reel — Movies account...")
    scripts["Instagram Reel (Movies)"] = write_movie_hook(digest)

    print("  [7/7] Instagram Reel — Gaming account...")
    scripts["Instagram Reel (Gaming)"] = write_gaming_script(digest)

    # Save individual script files
    scripts_dir = OUTPUT_DIR / date_str
    scripts_dir.mkdir(parents=True, exist_ok=True)

    for name, content in scripts.items():
        safe_name = name.lower().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")
        filepath = scripts_dir / f"{safe_name}.txt"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    # Save approval email draft
    email_draft = build_approval_email(scripts, date_str)
    email_path = scripts_dir / "00_approval_email_draft.txt"
    with open(email_path, "w", encoding="utf-8") as f:
        f.write(email_draft)

    # Save full bundle
    bundle_path = OUTPUT_DIR / f"bundle_{date_str}.json"
    with open(bundle_path, "w", encoding="utf-8") as f:
        json.dump({"date": date_str, "scripts": scripts}, f, indent=2, ensure_ascii=False)

    print(f"\n[DONE] {len(scripts)} scripts saved to {scripts_dir}")
    print(f"[DONE] Approval email draft: {email_path}")
    print(f"[DONE] Full bundle: {bundle_path}")
    print("\n--- NEWSLETTER PREVIEW ---")
    print(scripts["AI Newsletter"][:400])
    print("...")


if __name__ == "__main__":
    main()
