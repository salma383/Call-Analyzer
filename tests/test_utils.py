"""Tests for utils.py and criteria.py data integrity."""

import sys
import os
from io import BytesIO

# Allow imports from parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from criteria import CLIENT_CRITERIA, UNIVERSAL_RULES, LEAD_TEMPLATES, WHISPER_VOCAB
from utils import sanitize_filename, hash_audio_file, chunk_transcript, reconstruct_spelled_out


# ── criteria.py data integrity ───────────────────────────────────────────────

def test_client_criteria_required_keys():
    required = {
        "type", "dialer", "agent", "framework", "checklist",
        "hard_disqualifiers", "red_flags", "coaching_focus", "script_notes",
    }
    for name, c in CLIENT_CRITERIA.items():
        missing = required - c.keys()
        assert not missing, f"{name} missing keys: {missing}"


def test_client_criteria_types_valid():
    valid_types = {"real_estate", "business", "referral"}
    for name, c in CLIENT_CRITERIA.items():
        assert c["type"] in valid_types, f"{name} has invalid type: {c['type']}"


def test_checklists_non_empty():
    for name, c in CLIENT_CRITERIA.items():
        assert len(c["checklist"]) > 0, f"{name} has empty checklist"


def test_universal_rules_count():
    assert len(UNIVERSAL_RULES) == 10


def test_lead_templates_cover_all_types():
    types_used = {c["type"] for c in CLIENT_CRITERIA.values()}
    for t in types_used:
        assert t in LEAD_TEMPLATES, f"No template for type: {t}"


def test_whisper_vocab_not_empty():
    assert len(WHISPER_VOCAB) > 100


# ── sanitize_filename ────────────────────────────────────────────────────────

def test_sanitize_normal_name():
    assert sanitize_filename("Joy") == "Joy"


def test_sanitize_with_slashes():
    assert sanitize_filename("Joy / Team A") == "Joy_Team_A"


def test_sanitize_empty():
    assert sanitize_filename("") == "unnamed"


def test_sanitize_whitespace():
    assert sanitize_filename("   ") == "unnamed"


def test_sanitize_long_name():
    result = sanitize_filename("a" * 200)
    assert len(result) <= 100


def test_sanitize_special_chars():
    result = sanitize_filename("agent@name#1")
    assert "@" not in result
    assert "#" not in result


# ── hash_audio_file ──────────────────────────────────────────────────────────

def test_hash_consistent():
    f = BytesIO(b"fake audio content")
    h1 = hash_audio_file(f)
    h2 = hash_audio_file(f)
    assert h1 == h2


def test_hash_length():
    f = BytesIO(b"test data")
    assert len(hash_audio_file(f)) == 32  # MD5 hex


def test_hash_resets_seek():
    f = BytesIO(b"some audio bytes")
    hash_audio_file(f)
    assert f.tell() == 0


# ── chunk_transcript ─────────────────────────────────────────────────────────

def test_chunk_short_text():
    assert chunk_transcript("Short text", 1000) == ["Short text"]


def test_chunk_long_text():
    text = "Hello world. " * 5000  # ~65k chars
    chunks = chunk_transcript(text, 2000)
    assert len(chunks) > 1
    # Each chunk should be roughly within limit (with some tolerance)
    for c in chunks:
        assert len(c) <= 2000 * 4 + 500


def test_chunk_preserves_all_content():
    sentences = [f"Sentence {i}." for i in range(100)]
    text = " ".join(sentences)
    chunks = chunk_transcript(text, 500)
    rejoined = " ".join(chunks)
    # All sentences should be present
    for s in sentences:
        assert s in rejoined


# ── reconstruct_spelled_out ──────────────────────────────────────────────────

def test_reconstruct_spelled_email():
    text = "my email is s a l m a at gmail dot com"
    result = reconstruct_spelled_out(text)
    assert "salma@gmail.com" in result


def test_reconstruct_spelled_email_mixed():
    text = "it's j o h n at yahoo dot com"
    result = reconstruct_spelled_out(text)
    assert "john@yahoo.com" in result


def test_reconstruct_no_change_for_normal_text():
    text = "The property is located in a great neighborhood."
    assert reconstruct_spelled_out(text) == text


def test_reconstruct_empty():
    assert reconstruct_spelled_out("") == ""
    assert reconstruct_spelled_out(None) is None


def test_reconstruct_street_numbers():
    text = "the address is 1 2 3 Main Street"
    result = reconstruct_spelled_out(text)
    assert "123 Main" in result


def test_reconstruct_at_dot_in_email():
    text = "email me at john at gmail dot com"
    result = reconstruct_spelled_out(text)
    assert "john@gmail.com" in result
