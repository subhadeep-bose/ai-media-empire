"""
Platform metadata generator.
Takes a script + niche → YouTube title/description/tags + Instagram caption.
Uses the shared LLM module so Ollama→Groq fallback applies automatically.
"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from llm import call_llm
from config import GROQ_MAX_TOKENS_CONTENT

log = logging.getLogger(__name__)


def generate_youtube_metadata(script: str, niche: str) -> dict:
    prompt = f"""
You are a YouTube SEO specialist. Given this Reel/Short script for a {niche} channel,
generate YouTube metadata that maximises discoverability.

SCRIPT:
{script[:800]}

OUTPUT — return ONLY valid JSON, no markdown, no preamble:
{{
  "title": "<60 chars, includes primary keyword, no clickbait caps>",
  "description": "<150-200 words: hook sentence, 3 key points, CTA to subscribe, relevant keywords naturally woven in>",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10"],
  "category": "<YouTube category name>",
  "thumbnail_text": "<6 words max — text to overlay on thumbnail>"
}}

Rules:
- Title must be under 60 characters
- Include 10 tags, mix of broad and niche-specific
- No invented facts — base everything on the script above
- thumbnail_text should be the most shocking/curious line from the script
"""
    raw = call_llm(prompt, max_tokens=600)
    if raw.startswith("[ERROR]"):
        log.warning("Metadata LLM error for %s: %s", niche, raw)
        return {"error": raw}
    try:
        # Strip any markdown code fences if present
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except json.JSONDecodeError:
        log.warning("Could not parse metadata JSON for %s — returning raw", niche)
        return {"raw": raw}


def generate_instagram_caption(script: str, niche: str) -> str:
    prompt = f"""
You are an Instagram growth specialist. Write an Instagram caption for this Reel script.

SCRIPT:
{script[:600]}

NICHE: {niche}

FORMAT:
- Hook line (first 125 chars must stop the scroll — this shows before "more")
- 2-3 sentences expanding the hook
- 5 relevant hashtags (NO generic ones like #viral #fyp)
- CTA: "Follow for daily [niche] content"

Rules:
- No invented stats or facts not in the script
- Hashtags must be niche-specific and under 500K posts (avoids hashtag shadowban)
- Total length 150-220 words
Output ONLY the caption. No preamble.
"""
    result = call_llm(prompt, max_tokens=400)
    if result.startswith("[ERROR]"):
        log.warning("Instagram caption LLM error for %s: %s", niche, result)
    return result
