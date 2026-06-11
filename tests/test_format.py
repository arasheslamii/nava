"""Tier-1 formatter tests: dictionary, rules, pipeline (pure, no model)."""

from __future__ import annotations

from nava.format.dictionary import CustomDictionary
from nava.format.pipeline import FormatterPipeline
from nava.format.rules import Tier1RuleFormatter


# --- custom dictionary ---

def test_dictionary_corrects_proper_nouns():
    d = CustomDictionary({"mod capital": "MAAD Capital", "maloc": "MALLOC"})
    out, notes = d.apply("push to the mod capital repo and run maloc")
    assert "MAAD Capital" in out and "MALLOC" in out
    assert len(notes) == 2


def test_dictionary_is_case_insensitive_and_word_bounded():
    d = CustomDictionary({"venv": "venv-X"})
    # matches standalone token regardless of case…
    assert d.apply("activate the VENV now")[0] == "activate the venv-X now"
    # …but not inside another word
    assert d.apply("envenvenom")[0] == "envenvenom"


def test_dictionary_longest_phrase_wins():
    d = CustomDictionary({"capital": "CAP", "mad capital": "MAAD Capital"})
    assert d.apply("the mad capital fund")[0] == "the MAAD Capital fund"


def test_empty_dictionary_is_noop():
    d = CustomDictionary()
    assert d.apply("anything at all")[0] == "anything at all"


# --- rules ---

def test_removes_disfluencies_but_keeps_meaning():
    r = Tier1RuleFormatter()
    out = r.format("um, so I was thinking, you know, we could ship it").text
    assert "um" not in out.lower().split()
    assert "you know" not in out.lower()
    assert "thinking" in out and "ship it" in out.lower()


def test_capitalizes_sentences_and_standalone_i():
    r = Tier1RuleFormatter()
    out = r.format("hello there. i am fine").text
    assert out.startswith("Hello") and " I am" in out and out.endswith(".")


def test_does_not_break_decimal_into_sentence():
    r = Tier1RuleFormatter()
    out = r.format("the meeting moved to 3.30 on monday").text
    assert "3.30 on monday".replace("monday", "Monday") in out or "3.30 on" in out
    assert "3.30 On" not in out  # the decimal point must not trigger a capital


def test_terminal_punctuation_added_once():
    r = Tier1RuleFormatter()
    assert r.format("send the report").text.endswith(".")
    assert r.format("are you sure?").text.endswith("?")


# --- pipeline ---

def test_pipeline_dictionary_then_rules():
    d = CustomDictionary({"faster we swear": "faster-whisper"})
    p = FormatterPipeline(dictionary=d, rules=Tier1RuleFormatter())
    res = p.format("um, the faster we swear backend is great")
    assert "faster-whisper" in res.text
    assert "um" not in res.text.lower().split()
    assert res.text[0].isupper() and res.text.endswith(".")
    assert res.changed


def test_pipeline_disabled_is_passthrough():
    p = FormatterPipeline(enabled=False)
    res = p.format("um raw text")
    assert res.text == "um raw text" and not res.changed
