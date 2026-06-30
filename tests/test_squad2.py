"""
Unit tests for squad2_content/squad2_run.py — niche section extraction.
"""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from squad2_content.squad2_run import extract_niche_section, write_reel_sports, write_reel_movies, write_reel_gaming

DIGEST = """
## AI/Tech
- **Title**: Meta secretly used Google's Gemini
- **Source**: Reddit

## Gaming
- **Title**: Steam Deck update adds PS5 remote play
- **Source**: GitHub Trending

## Movies
- **Title**: New trailer drops for sci-fi epic
- **Source**: RSS
"""

DIGEST_NO_SPORTS = """
## AI/Tech
- **Title**: Meta secretly used Google's Gemini
"""


def test_extract_niche_section_returns_only_matching_section():
    section = extract_niche_section(DIGEST, ["Gaming"])
    assert "Steam Deck" in section
    assert "Gemini" not in section
    assert "sci-fi epic" not in section


def test_extract_niche_section_no_match_returns_empty():
    section = extract_niche_section(DIGEST_NO_SPORTS, ["Cricket", "Football", "WWE"])
    assert section == ""


def test_write_reel_sports_skips_without_llm_call_when_no_sports_section():
    with patch("squad2_content.squad2_run.call_llm") as mock_llm:
        result = write_reel_sports(DIGEST_NO_SPORTS)
        assert result == "NO SPORTS CONTENT TODAY"
        mock_llm.assert_not_called()


def test_write_reel_movies_skips_without_llm_call_when_no_movies_section():
    with patch("squad2_content.squad2_run.call_llm") as mock_llm:
        result = write_reel_movies(DIGEST_NO_SPORTS)
        assert result == "NO MOVIES CONTENT TODAY"
        mock_llm.assert_not_called()


def test_write_reel_gaming_skips_without_llm_call_when_no_gaming_section():
    with patch("squad2_content.squad2_run.call_llm") as mock_llm:
        result = write_reel_gaming(DIGEST_NO_SPORTS)
        assert result == "NO GAMING CONTENT TODAY"
        mock_llm.assert_not_called()


def test_write_reel_movies_calls_llm_with_only_movies_section():
    with patch("squad2_content.squad2_run.call_llm", return_value="script") as mock_llm:
        write_reel_movies(DIGEST)
        prompt = mock_llm.call_args[0][0]
        assert "sci-fi epic" in prompt
        assert "Gemini" not in prompt
        assert "Steam Deck" not in prompt
