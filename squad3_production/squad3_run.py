"""
Squad 3 — Multimedia Production
Reads Squad 2 approved scripts → TTS audio + SRT captions + platform metadata.
Output structure:
  squad3_output/YYYY-MM-DD/<niche>/
    audio.mp3
    captions.srt
    youtube_meta.json
    instagram_caption.txt
"""

import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import OUTPUT_DIR, REPO_ROOT
from tts import generate_audio, generate_srt
from metadata import generate_youtube_metadata, generate_instagram_caption

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("squad3")

SQUAD3_OUTPUT = REPO_ROOT / "squad3_output"

# Map script bundle keys → niche slug + whether to generate audio
NICHE_MAP = {
    "AI Newsletter":                  ("newsletter",    False),  # text-only
    "Twitter Thread (AI/Tech)":       ("twitter",       False),  # text-only
    "Instagram Reel (AI/Tech)":       ("ai_tech",       True),
    "Instagram Reel (Sports)":        ("sports",        True),
    "Instagram Reel (Bengali Books)": ("bengali_books", True),
    "Instagram Reel (Movies)":        ("movies",        True),
    "Instagram Reel (Gaming)":        ("gaming",        True),
}

SKIP_MARKERS = ["NO SPORTS CONTENT TODAY", "NO GAMING CONTENT TODAY",
                 "NO BENGALI BOOK CONTENT TODAY", "NO MOVIES CONTENT TODAY", "[ERROR]"]


def _should_skip(content: str) -> bool:
    return any(marker in content for marker in SKIP_MARKERS)


def process_niche(name: str, script: str, date_str: str) -> dict:
    niche_slug, do_audio = NICHE_MAP.get(name, ("unknown", False))
    out_dir = SQUAD3_OUTPUT / date_str / niche_slug
    out_dir.mkdir(parents=True, exist_ok=True)

    result = {"niche": niche_slug, "skipped": False, "audio": False,
              "srt": False, "youtube_meta": False, "instagram_caption": False}

    if _should_skip(script):
        log.info("Skipping %s — no content today", name)
        result["skipped"] = True
        return result

    # Save raw script copy
    (out_dir / "script.txt").write_text(script, encoding="utf-8")

    # TTS + captions for Reel scripts
    if do_audio:
        audio_path = out_dir / "audio.mp3"
        result["audio"] = generate_audio(script, niche_slug, audio_path)

        srt_path = out_dir / "captions.srt"
        generate_srt(script, srt_path)
        result["srt"] = True

    # YouTube metadata for all niches
    log.info("Generating YouTube metadata for %s...", name)
    yt_meta = generate_youtube_metadata(script, name)
    yt_path = out_dir / "youtube_meta.json"
    yt_path.write_text(json.dumps(yt_meta, indent=2, ensure_ascii=False), encoding="utf-8")
    result["youtube_meta"] = "error" not in yt_meta

    # Instagram caption for Reel scripts
    if do_audio:
        log.info("Generating Instagram caption for %s...", name)
        caption = generate_instagram_caption(script, name)
        (out_dir / "instagram_caption.txt").write_text(caption, encoding="utf-8")
        result["instagram_caption"] = not caption.startswith("[ERROR]")

    return result


def main():
    date_str = datetime.now().strftime("%Y-%m-%d")
    log.info("=" * 55)
    log.info("SQUAD 3: Multimedia production — %s", date_str)
    log.info("=" * 55)

    # Find today's bundle from Squad 2
    bundle_path = OUTPUT_DIR / f"bundle_{date_str}.json"
    if not bundle_path.exists():
        # Fall back to most recent bundle
        bundles = sorted(OUTPUT_DIR.glob("bundle_*.json"), reverse=True)
        if not bundles:
            log.error("No Squad 2 bundle found. Run Squad 2 first.")
            sys.exit(1)
        bundle_path = bundles[0]
        log.warning("Today's bundle not found — using %s", bundle_path.name)

    with open(bundle_path, encoding="utf-8") as f:
        bundle = json.load(f)

    scripts = bundle.get("scripts", {})
    log.info("Loaded %d scripts from %s", len(scripts), bundle_path.name)

    results = {}
    # max_workers=2 to be gentle on Groq TPM during metadata generation
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {
            pool.submit(process_niche, name, script, date_str): name
            for name, script in scripts.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception:
                log.exception("Failed processing %s", name)
                results[name] = {"error": True}

    # Summary
    log.info("=" * 55)
    log.info("SQUAD 3 COMPLETE")
    audio_count = sum(1 for r in results.values() if r.get("audio"))
    meta_count  = sum(1 for r in results.values() if r.get("youtube_meta"))
    skip_count  = sum(1 for r in results.values() if r.get("skipped"))
    log.info("Audio files:      %d", audio_count)
    log.info("YouTube metadata: %d", meta_count)
    log.info("Skipped (no data):%d", skip_count)
    log.info("Output dir:       %s", SQUAD3_OUTPUT / date_str)
    log.info("=" * 55)

    error_count = sum(1 for r in results.values() if r.get("error"))
    if error_count > 2:
        log.error("%d niches failed — check logs", error_count)
        sys.exit(1)


if __name__ == "__main__":
    main()
