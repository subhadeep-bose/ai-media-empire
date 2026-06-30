"""
Unit tests for notify.py
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import notify


# ── build_summary ───────────────────────────────────────────────────────────

def test_build_summary_no_roundup():
    summary = notify.build_summary("2026-06-30", {})
    assert "No Chief of Staff roundup found" in summary


def test_build_summary_with_roundup():
    roundup = {
        "note": "All agents reported in.",
        "items": [{"tag": "Virat Kohli", "text": "9 sources scraped"}],
    }
    summary = notify.build_summary("2026-06-30", roundup)
    assert "All agents reported in." in summary
    assert "Virat Kohli: 9 sources scraped" in summary


# ── post_github_issue ───────────────────────────────────────────────────────

def test_post_github_issue_skips_without_credentials():
    with patch.object(notify, "GITHUB_TOKEN", ""), \
         patch.object(notify, "GITHUB_REPOSITORY", ""), \
         patch("notify.requests.get") as mock_get, \
         patch("notify.requests.post") as mock_post:
        notify.post_github_issue("2026-06-30", "summary text")

    mock_get.assert_not_called()
    mock_post.assert_not_called()


def test_post_github_issue_creates_new_issue():
    mock_get_resp = MagicMock()
    mock_get_resp.json.return_value = []
    mock_post_resp = MagicMock()
    mock_post_resp.json.return_value = {"number": 42}

    with patch.object(notify, "GITHUB_TOKEN", "tok"), \
         patch.object(notify, "GITHUB_REPOSITORY", "owner/repo"), \
         patch("notify.requests.get", return_value=mock_get_resp), \
         patch("notify.requests.post", return_value=mock_post_resp) as mock_post:
        notify.post_github_issue("2026-06-30", "summary text", run_id="123")

    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert kwargs["json"]["title"] == "Daily roundup — 2026-06-30"
    assert "summary text" in kwargs["json"]["body"]


def test_post_github_issue_comments_on_existing_issue():
    mock_get_resp = MagicMock()
    mock_get_resp.json.return_value = [{"number": 7, "title": "Daily roundup — 2026-06-30"}]
    mock_post_resp = MagicMock()

    with patch.object(notify, "GITHUB_TOKEN", "tok"), \
         patch.object(notify, "GITHUB_REPOSITORY", "owner/repo"), \
         patch("notify.requests.get", return_value=mock_get_resp), \
         patch("notify.requests.post", return_value=mock_post_resp) as mock_post:
        notify.post_github_issue("2026-06-30", "summary text")

    mock_post.assert_called_once()
    args, _ = mock_post.call_args
    assert "issues/7/comments" in args[0]


# ── send_approval_email ─────────────────────────────────────────────────────

def test_send_approval_email_skips_without_credentials():
    with patch.object(notify, "SMTP_HOST", ""), \
         patch("notify.smtplib.SMTP") as mock_smtp:
        notify.send_approval_email("2026-06-30", "summary text")

    mock_smtp.assert_not_called()


def test_send_approval_email_sends_when_configured(tmp_path):
    mock_server = MagicMock()
    mock_smtp_cm = MagicMock()
    mock_smtp_cm.__enter__.return_value = mock_server

    with patch.object(notify, "SMTP_HOST", "smtp.example.com"), \
         patch.object(notify, "SMTP_USER", "bot@example.com"), \
         patch.object(notify, "SMTP_PASSWORD", "secret"), \
         patch.object(notify, "NOTIFY_EMAIL_TO", "me@example.com"), \
         patch.object(notify, "OUTPUT_DIR", tmp_path), \
         patch("notify.smtplib.SMTP", return_value=mock_smtp_cm) as mock_smtp:
        notify.send_approval_email("2026-06-30", "summary text")

    mock_smtp.assert_called_once()
    mock_server.login.assert_called_once_with("bot@example.com", "secret")
    mock_server.send_message.assert_called_once()
