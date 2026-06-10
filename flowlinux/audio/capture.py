"""16 kHz mono push-to-talk audio capture via sounddevice (PortAudio)."""

from __future__ import annotations

import threading
import wave
from dataclasses import dataclass

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16_000
CHANNELS = 1
DTYPE = "int16"


def resolve_input_device(preferred=None):
    """Pick a clean input device. Prefer PulseAudio/PipeWire (they resample to 16 kHz
    mono for us); fall back to the sounddevice default."""
    if preferred is not None:
        return preferred
    try:
        devices = sd.query_devices()
    except Exception:
        return None
    for wanted in ("pulse", "pipewire"):
        for idx, dev in enumerate(devices):
            if dev.get("max_input_channels", 0) > 0 and dev["name"] == wanted:
                return idx
    return None  # sounddevice default


@dataclass
class Recording:
    audio: np.ndarray  # 1-D int16
    sample_rate: int

    @property
    def duration_s(self) -> float:
        return len(self.audio) / self.sample_rate if self.sample_rate else 0.0

    @property
    def peak(self) -> int:
        # widen to int32 first: np.abs(int16(-32768)) overflows back to -32768
        return int(np.abs(self.audio.astype(np.int32)).max()) if len(self.audio) else 0


class AudioRecorder:
    """start() opens the input stream and buffers frames; stop() returns a Recording.

    A frame callback appends copies of the incoming buffers, so capture is decoupled
    from the (hotkey) thread that calls start/stop.
    """

    def __init__(self, sample_rate: int = SAMPLE_RATE, channels: int = CHANNELS,
                 device=None):
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = resolve_input_device(device)
        self._stream = None
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()

    def _callback(self, indata, frames, time_info, status) -> None:  # noqa: ARG002
        with self._lock:
            self._frames.append(indata.copy())

    def start(self) -> None:
        with self._lock:
            self._frames = []
        self._stream = sd.InputStream(
            samplerate=self.sample_rate, channels=self.channels, dtype=DTYPE,
            device=self.device, callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> Recording:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            audio = (np.concatenate(self._frames, axis=0).reshape(-1)
                     if self._frames else np.zeros(0, dtype=np.int16))
        return Recording(audio=audio, sample_rate=self.sample_rate)

    @property
    def is_recording(self) -> bool:
        return self._stream is not None


def record_fixed(seconds: float, sample_rate: int = SAMPLE_RATE, device=None) -> Recording:
    """Blocking fixed-duration capture (used for the headless mic self-test)."""
    dev = resolve_input_device(device)
    audio = sd.rec(int(seconds * sample_rate), samplerate=sample_rate,
                   channels=CHANNELS, dtype=DTYPE, device=dev)
    sd.wait()
    return Recording(audio=audio.reshape(-1), sample_rate=sample_rate)


def save_wav(rec: Recording, path: str) -> None:
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)  # int16
        w.setframerate(rec.sample_rate)
        w.writeframes(rec.audio.astype("<i2").tobytes())
