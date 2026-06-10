"""Load an audio file to 16 kHz mono float32 (via faster-whisper's bundled decoder)."""

from __future__ import annotations

import numpy as np


def load_audio_file(path: str, sample_rate: int = 16_000) -> np.ndarray:
    from faster_whisper.audio import decode_audio

    return decode_audio(path, sampling_rate=sample_rate)
