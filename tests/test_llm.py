"""
Unit tests for llm.py
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import llm as llm_module
from llm import call_groq, call_llm


# ── call_groq success ──────────────────────────────────────────────────────

def test_call_groq_success():
    """Valid choices response returns the message content."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "Hello from Groq"}}]
    }

    with patch.object(llm_module, "GROQ_API_KEY", "valid-key"), \
         patch("llm.requests.post", return_value=mock_resp) as mock_post:
        result = call_groq("test prompt")

    assert result == "Hello from Groq"
    mock_post.assert_called_once()


# ── call_groq error response ───────────────────────────────────────────────

def test_call_groq_error_response():
    """Non-choices response with error dict returns string starting with [ERROR]."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "error": {"code": "invalid_request", "message": "Bad parameter"}
    }

    with patch.object(llm_module, "GROQ_API_KEY", "valid-key"), \
         patch("llm.requests.post", return_value=mock_resp):
        result = call_groq("test prompt")

    assert result.startswith("[ERROR]")
    assert "Bad parameter" in result


# ── call_groq no key ──────────────────────────────────────────────────────

def test_call_groq_no_key():
    """Empty or placeholder key returns [ERROR] immediately without HTTP call."""
    with patch.object(llm_module, "GROQ_API_KEY", ""), \
         patch("llm.requests.post") as mock_post:
        result = call_groq("prompt")

    assert result.startswith("[ERROR]")
    mock_post.assert_not_called()

    with patch.object(llm_module, "GROQ_API_KEY", "your_groq_api_key_here"), \
         patch("llm.requests.post") as mock_post2:
        result2 = call_groq("prompt")

    assert result2.startswith("[ERROR]")
    mock_post2.assert_not_called()


# ── call_groq rate limit retry ────────────────────────────────────────────

def test_call_groq_rate_limit_retry():
    """Rate-limit response on first attempt triggers retry and eventually succeeds."""
    rate_limit_resp = MagicMock()
    rate_limit_resp.json.return_value = {
        "error": {"code": "rate_limit_exceeded", "message": "Too many requests"}
    }

    success_resp = MagicMock()
    success_resp.json.return_value = {
        "choices": [{"message": {"content": "Retry succeeded"}}]
    }

    with patch.object(llm_module, "GROQ_API_KEY", "valid-key"), \
         patch("llm.requests.post", side_effect=[rate_limit_resp, success_resp]), \
         patch("llm.time.sleep") as mock_sleep:
        result = call_groq("prompt")

    assert result == "Retry succeeded"
    # sleep should have been called once for the rate-limit wait
    mock_sleep.assert_called_once()


# ── call_llm prefers Ollama ───────────────────────────────────────────────

def test_call_llm_prefers_ollama():
    """call_llm returns Ollama result and never calls Groq when Ollama succeeds."""
    with patch("llm.call_ollama", return_value="Ollama answer") as mock_ollama, \
         patch("llm.call_groq") as mock_groq:
        result = call_llm("prompt")

    assert result == "Ollama answer"
    mock_ollama.assert_called_once()
    mock_groq.assert_not_called()


def test_call_llm_falls_back_to_groq():
    """call_llm falls back to Groq when Ollama returns None."""
    with patch("llm.call_ollama", return_value=None), \
         patch("llm.call_groq", return_value="Groq answer") as mock_groq:
        result = call_llm("prompt", max_tokens=500)

    assert result == "Groq answer"
    mock_groq.assert_called_once_with("prompt", 500)
