"""Tests for Squad 3 — stock footage sourcing and FFmpeg assembly."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from squad3_production.visuals import fetch_stock_clips, _pick_video_file
from squad3_production.video import assemble_video


# ── visuals.py ───────────────────────────────────────────────────────────────

def test_fetch_stock_clips_no_api_key_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("squad3_production.visuals.PEXELS_API_KEY", "")
    result = fetch_stock_clips("ai_tech", tmp_path)
    assert result == []


def test_fetch_stock_clips_downloads_files(tmp_path, monkeypatch):
    monkeypatch.setattr("squad3_production.visuals.PEXELS_API_KEY", "fake-key")
    mock_search_resp = MagicMock()
    mock_search_resp.json.return_value = {
        "videos": [{"video_files": [{"width": 1080, "link": "http://example.com/clip.mp4"}]}]
    }
    mock_search_resp.raise_for_status.return_value = None

    mock_dl_resp = MagicMock()
    mock_dl_resp.__enter__.return_value = mock_dl_resp
    mock_dl_resp.iter_content.return_value = [b"data"]
    mock_dl_resp.raise_for_status.return_value = None

    with patch("squad3_production.visuals.requests.get", side_effect=[mock_search_resp, mock_dl_resp]):
        result = fetch_stock_clips("ai_tech", tmp_path, count=1)

    assert len(result) == 1
    assert result[0].exists()


def test_fetch_stock_clips_search_failure_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("squad3_production.visuals.PEXELS_API_KEY", "fake-key")
    with patch("squad3_production.visuals.requests.get", side_effect=Exception("network error")):
        result = fetch_stock_clips("ai_tech", tmp_path)
    assert result == []


def test_pick_video_file_prefers_720p_or_above():
    video = {"video_files": [{"width": 360, "link": "small"}, {"width": 1080, "link": "big"}]}
    assert _pick_video_file(video) == "big"


def test_pick_video_file_no_files_returns_empty():
    assert _pick_video_file({"video_files": []}) == ""


# ── video.py ─────────────────────────────────────────────────────────────────

def test_assemble_video_no_clips_returns_false(tmp_path):
    result = assemble_video(tmp_path / "audio.mp3", tmp_path / "captions.srt", [], tmp_path / "out.mp4")
    assert result is False


def test_assemble_video_ffprobe_failure_returns_false(tmp_path):
    clip = tmp_path / "clip_0.mp4"
    clip.write_bytes(b"fake")
    with patch("squad3_production.video.get_audio_duration", side_effect=subprocess.CalledProcessError(1, "ffprobe")):
        result = assemble_video(tmp_path / "audio.mp3", tmp_path / "captions.srt", [clip], tmp_path / "out.mp4")
    assert result is False


def test_assemble_video_ffmpeg_failure_returns_false(tmp_path):
    clip = tmp_path / "clip_0.mp4"
    clip.write_bytes(b"fake")
    with patch("squad3_production.video.get_audio_duration", return_value=10.0), \
         patch("squad3_production.video.subprocess.run",
               side_effect=subprocess.CalledProcessError(1, "ffmpeg", stderr="boom")):
        result = assemble_video(tmp_path / "audio.mp3", tmp_path / "captions.srt", [clip], tmp_path / "out.mp4")
    assert result is False


def test_assemble_video_success_calls_ffmpeg_twice(tmp_path):
    clip = tmp_path / "clip_0.mp4"
    clip.write_bytes(b"fake")
    audio = tmp_path / "audio.mp3"
    audio.write_bytes(b"fake")
    srt = tmp_path / "captions.srt"
    srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nhi\n")
    out = tmp_path / "out.mp4"

    with patch("squad3_production.video.get_audio_duration", return_value=10.0), \
         patch("squad3_production.video.subprocess.run") as mock_run:
        result = assemble_video(audio, srt, [clip], out)

    assert result is True
    assert mock_run.call_count == 2
