"""Tests for telegram_bot.py — per-agent Telegram bot sender."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import telegram_bot


def test_send_agent_update_skips_without_token(tmp_path, monkeypatch):
    monkeypatch.setattr(telegram_bot, "REPORTS_DIR", tmp_path)
    with patch.object(telegram_bot, "TELEGRAM_BOT_TOKENS", {"squad1_intel": ""}), \
         patch.object(telegram_bot, "TELEGRAM_CHAT_ID", "chat123"), \
         patch("telegram_bot.requests.post") as mock_post:
        telegram_bot.send_agent_update("squad1_intel", "2026-06-30")

    mock_post.assert_not_called()


def test_send_agent_update_skips_without_chat_id(tmp_path, monkeypatch):
    monkeypatch.setattr(telegram_bot, "REPORTS_DIR", tmp_path)
    with patch.object(telegram_bot, "TELEGRAM_BOT_TOKENS", {"squad1_intel": "tok"}), \
         patch.object(telegram_bot, "TELEGRAM_CHAT_ID", ""), \
         patch("telegram_bot.requests.post") as mock_post:
        telegram_bot.send_agent_update("squad1_intel", "2026-06-30")

    mock_post.assert_not_called()


def test_send_agent_update_skips_without_report_card(tmp_path, monkeypatch):
    monkeypatch.setattr(telegram_bot, "REPORTS_DIR", tmp_path)
    with patch.object(telegram_bot, "TELEGRAM_BOT_TOKENS", {"squad1_intel": "tok"}), \
         patch.object(telegram_bot, "TELEGRAM_CHAT_ID", "chat123"), \
         patch("telegram_bot.requests.post") as mock_post:
        telegram_bot.send_agent_update("squad1_intel", "2026-06-30")

    mock_post.assert_not_called()


def test_send_agent_update_sends_photo_when_png_available(tmp_path, monkeypatch):
    monkeypatch.setattr(telegram_bot, "REPORTS_DIR", tmp_path)
    out_dir = tmp_path / "2026-06-30"
    out_dir.mkdir()
    (out_dir / "squad1_intel.html").write_text("<html></html>", encoding="utf-8")
    (out_dir / "squad1_intel.json").write_text(
        json.dumps({"note": "All good today."}), encoding="utf-8",
    )
    png_path = out_dir / "squad1_intel.png"

    def fake_render(html_path, out_png):
        out_png.write_bytes(b"fake-png")
        return out_png

    mock_resp = MagicMock()
    with patch.object(telegram_bot, "TELEGRAM_BOT_TOKENS", {"squad1_intel": "tok"}), \
         patch.object(telegram_bot, "TELEGRAM_CHAT_ID", "chat123"), \
         patch("telegram_bot.render_html_to_png", side_effect=fake_render), \
         patch("telegram_bot.requests.post", return_value=mock_resp) as mock_post:
        telegram_bot.send_agent_update("squad1_intel", "2026-06-30")

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert "sendPhoto" in args[0]
    assert "tok" in args[0]
    assert kwargs["data"]["chat_id"] == "chat123"
    assert png_path.exists()


def test_send_agent_update_falls_back_to_text_without_png(tmp_path, monkeypatch):
    monkeypatch.setattr(telegram_bot, "REPORTS_DIR", tmp_path)
    out_dir = tmp_path / "2026-06-30"
    out_dir.mkdir()
    (out_dir / "squad1_intel.html").write_text("<html></html>", encoding="utf-8")
    (out_dir / "squad1_intel.json").write_text(
        json.dumps({"note": "All good today."}), encoding="utf-8",
    )

    mock_resp = MagicMock()
    with patch.object(telegram_bot, "TELEGRAM_BOT_TOKENS", {"squad1_intel": "tok"}), \
         patch.object(telegram_bot, "TELEGRAM_CHAT_ID", "chat123"), \
         patch("telegram_bot.render_html_to_png", return_value=None), \
         patch("telegram_bot.requests.post", return_value=mock_resp) as mock_post:
        telegram_bot.send_agent_update("squad1_intel", "2026-06-30")

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert "sendMessage" in args[0]
    assert kwargs["data"]["chat_id"] == "chat123"
    assert "All good today." in kwargs["data"]["text"]
