"""faster-whisper (CTranslate2) backend — CPU baseline and GPU (set device='cuda')."""

from __future__ import annotations

import time

import numpy as np

from .base import ASRBackend, Segment, TranscriptionResult
from .postprocess import HallucinationThresholds, filter_segments

# Accuracy-first defaults (priorities #1/#2). condition_on_previous_text=False and the
# no_speech/log_prob thresholds + temperature fallback are the anti-hallucination guard.
_TEMPERATURE_FALLBACK = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]


class FasterWhisperBackend(ASRBackend):
    def __init__(
        self,
        model_size: str = "small.en",
        device: str = "cpu",
        compute_type: str = "int8",
        beam_size: int = 5,
        language: str = "en",
        vad: bool = True,
        cpu_threads: int = 0,
        thresholds: HallucinationThresholds | None = None,
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.beam_size = beam_size
        self.language = language
        self.vad = vad
        self.cpu_threads = cpu_threads
        self.thresholds = thresholds or HallucinationThresholds()
        self._model = None
        self.name = f"faster-whisper:{model_size}:{device}:{compute_type}"

    def load(self) -> None:
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=self.cpu_threads,
            )

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16_000) -> TranscriptionResult:
        self.load()
        samples = (audio.astype(np.float32) / 32768.0
                   if audio.dtype == np.int16 else audio.astype(np.float32))
        duration = len(samples) / sample_rate if sample_rate else 0.0

        t0 = time.monotonic()
        seg_iter, info = self._model.transcribe(
            samples,
            language=self.language,
            beam_size=self.beam_size,
            condition_on_previous_text=False,      # stop noise-induced repetition loops
            temperature=_TEMPERATURE_FALLBACK,     # fallback on low-confidence decodes
            no_speech_threshold=0.6,
            log_prob_threshold=-1.0,
            compression_ratio_threshold=2.4,
            vad_filter=self.vad,                   # Silero VAD gating (bundled)
            vad_parameters={"min_silence_duration_ms": 300} if self.vad else None,
        )
        segs = [
            Segment(
                text=s.text, start=s.start, end=s.end,
                avg_logprob=s.avg_logprob, no_speech_prob=s.no_speech_prob,
                compression_ratio=s.compression_ratio,
            )
            for s in seg_iter  # iterating triggers the actual decode
        ]
        infer_s = time.monotonic() - t0

        kept, dropped = filter_segments(segs, self.thresholds)
        text = "".join(s.text for s in kept).strip()
        return TranscriptionResult(
            text=text, segments=kept, language=getattr(info, "language", self.language),
            duration_s=duration, infer_s=infer_s, backend=self.name, dropped=dropped,
        )

    def unload(self) -> None:
        self._model = None
