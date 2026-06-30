"""
FFmpeg-based video assembly: concatenates stock clips, crops/scales to a
vertical Reel frame, trims to the narration's length, and burns in the
SRT captions over the voiceover track.
Requires the `ffmpeg`/`ffprobe` binaries on PATH (preinstalled on
GitHub Actions ubuntu-latest runners).
"""

import logging
import subprocess
from pathlib import Path

from config import VIDEO_WIDTH, VIDEO_HEIGHT

log = logging.getLogger(__name__)


def get_audio_duration(audio_path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def assemble_video(audio_path: Path, srt_path: Path, clip_paths: list, output_path: Path) -> bool:
    """
    Build output_path (.mp4) from audio_path + srt_path + clip_paths.
    Returns False (not an exception) if clip_paths is empty or ffmpeg fails —
    callers should treat that as "no video this run", not a hard error.
    """
    if not clip_paths:
        log.warning("No stock clips provided — skipping video assembly for %s", output_path)
        return False

    try:
        duration = get_audio_duration(audio_path)
    except Exception:
        log.exception("ffprobe failed to read duration of %s", audio_path)
        return False

    concat_file = output_path.parent / "_concat_list.txt"
    silent_path = output_path.parent / "_silent.mp4"

    try:
        with open(concat_file, "w", encoding="utf-8") as f:
            for clip in clip_paths:
                f.write(f"file '{clip.resolve()}'\n")

        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
                "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
                       f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}",
                "-an", "-t", str(duration), str(silent_path),
            ],
            check=True, capture_output=True, text=True,
        )

        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(silent_path), "-i", str(audio_path),
                "-vf", f"subtitles={srt_path}",
                "-c:v", "libx264", "-c:a", "aac", "-shortest", str(output_path),
            ],
            check=True, capture_output=True, text=True,
        )
        log.info("Video assembled: %s (%.1fs)", output_path.name, duration)
        return True
    except subprocess.CalledProcessError as e:
        log.error("ffmpeg failed for %s: %s", output_path, e.stderr[-500:] if e.stderr else e)
        return False
    finally:
        concat_file.unlink(missing_ok=True)
        silent_path.unlink(missing_ok=True)
