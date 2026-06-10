"""Audio capture + feedback (M2) and VAD/denoise (M3).

M2: `capture.py` (sounddevice 16 kHz mono AudioRecorder + record_fixed + save_wav),
`feedback.py` (beeps + libnotify cues). M3 adds Silero VAD gating and an optional
pre-model denoise (noisereduce / RNNoise) benchmarked for WER.
"""
