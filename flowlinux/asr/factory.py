"""Construct an ASR backend from simple parameters."""

from __future__ import annotations

from .base import ASRBackend
from .faster_whisper_backend import FasterWhisperBackend

CPU_DEFAULT_MODEL = "small.en"      # accuracy-leaning English CPU baseline
GPU_DEFAULT_MODEL = "distil-large-v3"  # English, ~1.5GB int8 (GPU path, M3 step 2)


def build_backend(
    engine: str = "faster-whisper",
    model: str | None = None,
    device: str = "cpu",
    compute_type: str = "int8",
    **kw,
) -> ASRBackend:
    engine = (engine or "faster-whisper").lower()
    if engine in ("faster-whisper", "fw", "faster_whisper"):
        if model is None:
            model = CPU_DEFAULT_MODEL if device == "cpu" else GPU_DEFAULT_MODEL
        return FasterWhisperBackend(
            model_size=model, device=device, compute_type=compute_type, **kw
        )
    # whisper.cpp-CUDA backend lands in M3 step 2.
    raise ValueError(f"unknown ASR engine: {engine!r}")
