"""ASR backends (M3).

`base.py` ASRBackend interface + result types; `faster_whisper_backend.py` (CT2; CPU
baseline now, GPU in step 2); `postprocess.py` anti-hallucination filter; `factory.py`
builder. whisper.cpp-CUDA + cloud backends slot in behind ASRBackend; the M3 benchmark
picks the default (ADR-0005).
"""

from .base import ASRBackend, Segment, TranscriptionResult
from .factory import build_backend

__all__ = ["ASRBackend", "Segment", "TranscriptionResult", "build_backend"]
