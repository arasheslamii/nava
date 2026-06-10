"""Non-GUI feedback cues: short beeps + desktop notifications (ADR-0007)."""

from __future__ import annotations

import shutil
import subprocess
import threading

_PLAY_SR = 44_100


def _beep(frequency: float, duration: float, volume: float) -> None:
    try:
        import numpy as np
        import sounddevice as sd

        t = np.linspace(0, duration, int(_PLAY_SR * duration), endpoint=False)
        # short fade in/out to avoid clicks
        env = np.minimum(1.0, np.minimum(t, duration - t) * 50)
        tone = (volume * env * np.sin(2 * np.pi * frequency * t)).astype("float32")
        sd.play(tone, _PLAY_SR)
        sd.wait()
    except Exception:
        pass  # audio cue is best-effort; never break the capture loop


def beep(frequency: float = 880, duration: float = 0.10, volume: float = 0.2) -> None:
    _beep(frequency, duration, volume)


def beep_async(frequency: float = 880, duration: float = 0.10, volume: float = 0.2) -> None:
    threading.Thread(target=_beep, args=(frequency, duration, volume), daemon=True).start()


def start_cue() -> None:
    beep_async(frequency=880, duration=0.10)   # rising "listening"


def stop_cue() -> None:
    beep_async(frequency=520, duration=0.10)   # lower "done"


def notify(title: str, message: str = "") -> None:
    if shutil.which("notify-send"):
        try:
            subprocess.run(["notify-send", "-a", "FlowLinux", "-t", "1500", title, message],
                           capture_output=True, timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            pass
