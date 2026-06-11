"""Load an audio file to 16 kHz mono float32.

Prefers soundfile (libsndfile: wav/flac/ogg) so we don't depend on faster-whisper's
av/ffmpeg decoder (which has no cp312 wheel for the CT2-3.24 GPU env). Falls back to
faster-whisper's decode_audio if soundfile can't read the file.
"""

from __future__ import annotations

import numpy as np


def _resample_linear(data: np.ndarray, src_sr: int, dst_sr: int) -> np.ndarray:
    if src_sr == dst_sr:
        return data
    n = int(round(len(data) * dst_sr / src_sr))
    x_old = np.arange(len(data))
    x_new = np.linspace(0, len(data), n, endpoint=False)
    return np.interp(x_new, x_old, data).astype(np.float32)


def load_audio_file(path: str, sample_rate: int = 16_000) -> np.ndarray:
    try:
        import soundfile as sf

        data, sr = sf.read(path, dtype="float32", always_2d=False)
        if data.ndim > 1:                      # mix to mono
            data = data.mean(axis=1)
        return _resample_linear(data.astype(np.float32), sr, sample_rate)
    except Exception:
        from faster_whisper.audio import decode_audio

        return decode_audio(path, sampling_rate=sample_rate)
