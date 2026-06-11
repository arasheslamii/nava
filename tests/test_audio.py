"""Audio Recording / WAV round-trip tests (no real device opened)."""

from __future__ import annotations

import wave

import numpy as np

from nava.audio.capture import Recording, save_wav


def test_recording_duration_and_peak():
    audio = np.array([0, 100, -32768, 32767, 0], dtype=np.int16)
    rec = Recording(audio=audio, sample_rate=16_000)
    assert rec.peak == 32768  # abs of int16 min
    assert abs(rec.duration_s - 5 / 16_000) < 1e-9


def test_empty_recording():
    rec = Recording(audio=np.zeros(0, dtype=np.int16), sample_rate=16_000)
    assert rec.duration_s == 0.0 and rec.peak == 0


def test_save_wav_roundtrip(tmp_path):
    sr = 16_000
    samples = (np.sin(np.linspace(0, 50, sr)) * 1000).astype(np.int16)
    rec = Recording(audio=samples, sample_rate=sr)
    path = tmp_path / "out.wav"
    save_wav(rec, str(path))

    with wave.open(str(path), "rb") as w:
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.getframerate() == sr
        assert w.getnframes() == len(samples)
        back = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
    assert np.array_equal(back, samples)
