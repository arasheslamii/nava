"""Anti-hallucination post-filtering (pure, unit-testable).

Whisper invents text on silence/noise (classic: "Thank you.", "Thanks for watching!").
VAD upstream removes most non-speech; this is the safety net for noise that slips through.
"""

from __future__ import annotations

from dataclasses import dataclass

from .base import Segment


@dataclass
class HallucinationThresholds:
    no_speech_prob: float = 0.6       # >= this (with low logprob) => likely silence
    avg_logprob: float = -1.0         # < this => low confidence
    compression_ratio: float = 2.4    # > this => repetitive/looping text
    min_chars: int = 1


# Frequent Whisper hallucinations on near-silence (lowercased, stripped).
COMMON_HALLUCINATIONS = {
    "thank you.", "thank you", "thanks for watching!", "thanks for watching.",
    "thank you very much.", "thank you for watching.", "thank you so much for watching.",
    "please subscribe.", "subscribe.", "you", ".", "...", "bye.", "bye bye.",
    "♪", "[music]", "(music)", "[silence]",
}


def is_hallucinated_segment(seg: Segment, th: HallucinationThresholds) -> bool:
    t = seg.text.strip().lower()
    if len(t) < th.min_chars:
        return True
    # high no-speech probability AND low confidence => silence misfire
    if seg.no_speech_prob >= th.no_speech_prob and seg.avg_logprob < th.avg_logprob:
        return True
    # runaway repetition
    if seg.compression_ratio > th.compression_ratio:
        return True
    # canned filler phrase with non-trivial no-speech probability
    if t in COMMON_HALLUCINATIONS and seg.no_speech_prob >= 0.4:
        return True
    return False


def filter_segments(
    segments: list[Segment], th: HallucinationThresholds | None = None
) -> tuple[list[Segment], int]:
    th = th or HallucinationThresholds()
    kept: list[Segment] = []
    dropped = 0
    for s in segments:
        if is_hallucinated_segment(s, th):
            dropped += 1
        else:
            kept.append(s)
    return kept, dropped
