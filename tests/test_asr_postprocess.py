"""Anti-hallucination filter tests (pure; no model loaded)."""

from __future__ import annotations

from flowlinux.asr.base import Segment
from flowlinux.asr.postprocess import (
    HallucinationThresholds,
    filter_segments,
    is_hallucinated_segment,
)

TH = HallucinationThresholds()


def seg(text, no_speech=0.0, logprob=0.0, comp=1.0):
    return Segment(text=text, start=0.0, end=1.0, avg_logprob=logprob,
                   no_speech_prob=no_speech, compression_ratio=comp)


def test_keeps_clean_speech():
    assert not is_hallucinated_segment(
        seg("Hello there, a normal sentence.", no_speech=0.05, logprob=-0.2, comp=1.4), TH)


def test_drops_empty():
    assert is_hallucinated_segment(seg("   "), TH)


def test_drops_silence_misfire():
    # high no-speech prob + low logprob => invented text on silence
    assert is_hallucinated_segment(seg("Thank you.", no_speech=0.9, logprob=-1.5), TH)


def test_drops_common_phrase_on_moderate_no_speech():
    assert is_hallucinated_segment(seg("Thanks for watching!", no_speech=0.5, logprob=-0.3), TH)


def test_keeps_real_thank_you_when_clearly_speech():
    # genuine "Thank you." with low no-speech prob must survive
    assert not is_hallucinated_segment(seg("Thank you.", no_speech=0.05, logprob=-0.2), TH)


def test_drops_repetition_loop():
    assert is_hallucinated_segment(
        seg("no no no no no no no", no_speech=0.1, logprob=-0.3, comp=3.0), TH)


def test_filter_counts_and_keeps_order():
    segs = [
        seg("Hello world.", 0.05, -0.2, 1.3),
        seg("Thank you.", 0.9, -1.5),     # silence misfire
        seg("   ", 0.0, 0.0),              # empty
    ]
    kept, dropped = filter_segments(segs)
    assert dropped == 2
    assert [s.text for s in kept] == ["Hello world."]
