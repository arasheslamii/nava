"""ASR integration tests — load a real Whisper model (gated; downloads on first run).

Run with:  NAVA_ASR_INTEGRATION=1 pytest tests/test_asr_integration.py -q
"""

from __future__ import annotations

import os

import numpy as np
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("NAVA_ASR_INTEGRATION") != "1",
    reason="set NAVA_ASR_INTEGRATION=1 to run (loads/downloads a Whisper model)",
)


def _backend():
    from nava.asr.factory import build_backend

    return build_backend(engine="faster-whisper", model="small.en", device="cpu")


def test_silence_transcribes_to_empty():
    """Golden anti-hallucination test: silence in -> empty out, never invented text."""
    audio = np.zeros(16_000 * 3, dtype=np.int16)
    res = _backend().transcribe(audio, 16_000)
    assert res.text == "", f"hallucinated on silence: {res.text!r}"


def test_white_noise_transcribes_to_empty():
    """Low-level noise (no speech) must also yield empty."""
    rng = np.random.default_rng(0)
    noise = (rng.normal(0, 200, 16_000 * 3)).astype(np.int16)
    res = _backend().transcribe(noise, 16_000)
    assert res.text == "", f"hallucinated on noise: {res.text!r}"
