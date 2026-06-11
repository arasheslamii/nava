"""ASR backend interface and result types (M3)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Segment:
    text: str
    start: float
    end: float
    avg_logprob: float = 0.0
    no_speech_prob: float = 0.0
    compression_ratio: float = 0.0


@dataclass
class TranscriptionResult:
    text: str
    segments: list[Segment] = field(default_factory=list)
    language: str = "en"
    duration_s: float = 0.0  # audio length
    infer_s: float = 0.0     # transcription wall-clock time
    backend: str = ""
    dropped: int = 0         # segments removed as hallucinated/low-confidence

    @property
    def rtf(self) -> float:
        """Real-time factor: infer_s / audio seconds (<1 is faster than real time)."""
        return (self.infer_s / self.duration_s) if self.duration_s else 0.0


class ASRBackend(ABC):
    """One speech-to-text backend. Lazily loads its model so idle RAM stays low."""

    name: str = "asr"

    @abstractmethod
    def load(self) -> None:
        """Load the model (idempotent)."""

    @abstractmethod
    def transcribe(self, audio: np.ndarray, sample_rate: int = 16_000) -> TranscriptionResult:
        """Transcribe 16 kHz mono audio (int16 or float32 [-1,1]). Must not raise on empty."""

    def unload(self) -> None:
        """Free the model (memory discipline). Default: no-op."""
