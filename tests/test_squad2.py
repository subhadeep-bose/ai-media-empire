"""
Unit tests for squad2_content/squad2_run.py — niche section extraction.
"""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from squad2_content.squad2_run import (
    extract_niche_section, write_reel_sports, write_reel_movies, write_reel_gaming,
    write_reel_ai, write_newsletter, write_twitter_thread, write_reel_bengali,
    write_twitter_hot_take, write_twitter_weekly_poll,
)

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

## Cricket
- **Title**: India drop Yastika Bhatia and pick G Kamalini for Asian Games
- **Source**: ESPNcricinfo

## WWE
- **Title**: Roman Reigns to defend title against Seth Rollins
- **Source**: WWE.com
"""

DIGEST_NO_SPORTS = """
## AI/Tech
- **Title**: Meta secretly used Google's Gemini
"""

DIGEST_NO_AI_TECH = """
## Cricket
- **Title**: India drop Yastika Bhatia and pick G Kamalini for Asian Games
"""

# Digest using ### niche headers with #### sub-headings (as seen in production runs)
DIGEST_SUBHEADINGS = """
# Daily Intel Digest — 2026-07-01
### AI/Tech
#### Top 2 Items
| Open-source AI tool | GitHub | Helps developers. | "AI Security Shield" |
| Google Agents CLI | GitHub | Build AI agents. | "Unleash AI Agents" |
### Gaming
#### Top 2 Items
| Steam Deck update | Reddit | New remote play. | "Steam Deck Drops" |
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


def test_write_newsletter_skips_without_llm_call_when_no_ai_tech_section():
    with patch("squad2_content.squad2_run.call_llm") as mock_llm:
        result = write_newsletter(DIGEST_NO_AI_TECH)
        assert result == "NO AI/TECH CONTENT TODAY"
        mock_llm.assert_not_called()


def test_write_newsletter_calls_llm_with_only_ai_tech_section():
    with patch("squad2_content.squad2_run.call_llm", return_value="newsletter") as mock_llm:
        write_newsletter(DIGEST)
        prompt = mock_llm.call_args[0][0]
        assert "Gemini" in prompt
        assert "Yastika Bhatia" not in prompt
        assert "Roman Reigns" not in prompt


def test_write_twitter_thread_skips_without_llm_call_when_no_ai_tech_section():
    with patch("squad2_content.squad2_run.call_llm") as mock_llm:
        result = write_twitter_thread(DIGEST_NO_AI_TECH)
        assert result == "NO AI/TECH CONTENT TODAY"
        mock_llm.assert_not_called()


def test_write_twitter_thread_calls_llm_with_only_ai_tech_section():
    with patch("squad2_content.squad2_run.call_llm", return_value="thread") as mock_llm:
        write_twitter_thread(DIGEST)
        prompt = mock_llm.call_args[0][0]
        assert "Gemini" in prompt
        assert "Yastika Bhatia" not in prompt
        assert "Roman Reigns" not in prompt


def test_write_reel_ai_skips_without_llm_call_when_no_ai_tech_section():
    with patch("squad2_content.squad2_run.call_llm") as mock_llm:
        result = write_reel_ai(DIGEST_NO_AI_TECH)
        assert result == "NO AI/TECH CONTENT TODAY"
        mock_llm.assert_not_called()


def test_write_reel_ai_calls_llm_with_only_ai_tech_section():
    with patch("squad2_content.squad2_run.call_llm", return_value="script") as mock_llm:
        write_reel_ai(DIGEST)
        prompt = mock_llm.call_args[0][0]
        assert "Gemini" in prompt
        assert "Yastika Bhatia" not in prompt
        assert "Roman Reigns" not in prompt


def test_extract_niche_section_captures_content_under_sub_headings():
    section = extract_niche_section(DIGEST_SUBHEADINGS, ["AI/Tech"])
    assert "Open-source AI tool" in section
    assert "Google Agents CLI" in section
    assert "Steam Deck" not in section


def test_extract_niche_section_sub_heading_does_not_stop_capture():
    section = extract_niche_section(DIGEST_SUBHEADINGS, ["Gaming"])
    assert "Steam Deck" in section
    assert "Open-source AI tool" not in section


def test_write_reel_bengali_skips_without_llm_call_when_no_book_data():
    with patch("squad2_content.squad2_run.call_llm") as mock_llm:
        result = write_reel_bengali(DIGEST_NO_SPORTS)
        assert result == "NO BENGALI BOOK CONTENT TODAY"
        mock_llm.assert_not_called()


def test_write_reel_bengali_calls_llm_when_book_data_present():
    digest_with_book = DIGEST + "\nAuthor: Rabindranath Tagore\nPlot: A tale of love and loss."
    with patch("squad2_content.squad2_run.call_llm", return_value="script") as mock_llm:
        result = write_reel_bengali(digest_with_book)
        assert result == "script"
        mock_llm.assert_called_once()


def test_write_twitter_thread_produces_7_tweet_prompt():
    with patch("squad2_content.squad2_run.call_llm", return_value="thread") as mock_llm:
        write_twitter_thread(DIGEST)
        prompt = mock_llm.call_args[0][0]
        assert "7-tweet" in prompt
        assert "Tweet 7" in prompt


def test_write_twitter_hot_take_skips_without_llm_when_no_ai_tech():
    with patch("squad2_content.squad2_run.call_llm") as mock_llm:
        result = write_twitter_hot_take(DIGEST_NO_AI_TECH)
        assert result == "NO AI/TECH CONTENT TODAY"
        mock_llm.assert_not_called()


def test_write_twitter_hot_take_calls_llm_with_only_ai_tech_section():
    with patch("squad2_content.squad2_run.call_llm", return_value="AI is overrated.") as mock_llm:
        result = write_twitter_hot_take(DIGEST)
        assert result == "AI is overrated."
        prompt = mock_llm.call_args[0][0]
        assert "Gemini" in prompt
        assert "Yastika Bhatia" not in prompt
        assert "Roman Reigns" not in prompt


def test_write_twitter_weekly_poll_skips_on_non_monday():
    with patch("squad2_content.squad2_run.call_llm") as mock_llm:
        with patch("squad2_content.squad2_run._dt") as mock_dt:
            mock_dt.datetime.now.return_value.weekday.return_value = 1  # Tuesday
            result = write_twitter_weekly_poll(DIGEST)
        assert result == "NO POLL TODAY"
        mock_llm.assert_not_called()


def test_write_twitter_weekly_poll_returns_json_on_monday():
    import json
    poll_json = '{"question": "Which AI tool do you use most?", "options": ["ChatGPT", "Claude", "Gemini", "Other"]}'
    with patch("squad2_content.squad2_run.call_llm", return_value=poll_json):
        with patch("squad2_content.squad2_run._dt") as mock_dt:
            mock_dt.datetime.now.return_value.weekday.return_value = 0  # Monday
            result = write_twitter_weekly_poll(DIGEST)
    parsed = json.loads(result)
    assert "question" in parsed
    assert len(parsed["options"]) == 4


def test_write_twitter_weekly_poll_skips_invalid_json_on_monday():
    with patch("squad2_content.squad2_run.call_llm", return_value="not valid json"):
        with patch("squad2_content.squad2_run._dt") as mock_dt:
            mock_dt.datetime.now.return_value.weekday.return_value = 0  # Monday
            result = write_twitter_weekly_poll(DIGEST)
    assert result == "NO POLL TODAY"
