"""ASR backends (M3).

Planned: one ASRBackend interface with FasterWhisper (CTranslate2 3.24, GPU int8 /
CPU int8) AND WhisperCpp (GGML_CUDA), plus opt-in cloud (Groq/Deepgram). The M3
benchmark picks the default on this Maxwell GPU and locks it in DECISIONS.md.
Model is tiered by resolved compute path (GPU: distil-large-v3 int8; CPU: base/small).
Stub until M3.
"""
