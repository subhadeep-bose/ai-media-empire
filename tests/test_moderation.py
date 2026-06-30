"""Tests for moderation.py — Squad 3's pre-assembly denylist check."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from moderation import flagged_terms


def test_flagged_terms_returns_empty_for_clean_script():
    assert flagged_terms("Here's today's top AI news roundup.") == []


def test_flagged_terms_catches_denylisted_phrase_case_insensitively():
    assert "kill yourself" in flagged_terms("Some text with KILL YOURSELF in it.")


def test_flagged_terms_returns_all_matches():
    text = "how to make a bomb and also credit card number leaks"
    hits = flagged_terms(text)
    assert "how to make a bomb" in hits
    assert "credit card number" in hits
