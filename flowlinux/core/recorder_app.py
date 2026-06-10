"""M2 recorder daemon: wires the PTT hotkey to audio capture + feedback.

This is the end-to-end loop for M2 (hold key → record → save WAV). M3 will replace
`on_utterance` with the ASR pipeline instead of (or in addition to) saving a WAV.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from ..audio import feedback
from ..audio.capture import AudioRecorder, Recording, save_wav
from ..hotkey.base import PTTController, PTTMode
from ..hotkey.pynput_x11 import PynputX11Hotkey


def default_out_dir() -> Path:
    base = Path.home() / ".cache" / "flowlinux" / "recordings"
    return base


class RecorderApp:
    def __init__(
        self,
        mode: PTTMode = PTTMode.HOLD,
        key: str = "ctrl_r",
        device=None,
        out_dir: Optional[Path] = None,
        feedback_enabled: bool = True,
        save: bool = True,
        once: bool = False,
        on_utterance: Optional[Callable[[Recording, Optional[Path]], None]] = None,
    ):
        self.recorder = AudioRecorder(device=device)
        self.controller = PTTController(self._on_start, self._on_stop, mode=mode)
        self.hotkey = PynputX11Hotkey(self.controller, key=key)
        self.key = self.hotkey.key_name
        self.mode = PTTMode(mode)
        self.out_dir = Path(out_dir) if out_dir else default_out_dir()
        self.feedback_enabled = feedback_enabled
        self.save = save
        self.once = once
        self.on_utterance = on_utterance
        self._done = threading.Event()
        self.last_path: Optional[Path] = None
        self.last_recording: Optional[Recording] = None

    # --- PTT callbacks (run on the hotkey listener thread) ---
    def _on_start(self) -> None:
        if self.feedback_enabled:
            feedback.start_cue()
            feedback.notify("FlowLinux", "Listening…")
        try:
            self.recorder.start()
        except Exception as e:  # mic failure must not crash the daemon
            print(f"[flowlinux] capture failed to start: {e}")
            if self.feedback_enabled:
                feedback.notify("FlowLinux", f"Mic error: {e}")

    def _on_stop(self) -> None:
        try:
            rec = self.recorder.stop()
        except Exception as e:
            print(f"[flowlinux] capture stop failed: {e}")
            return
        if self.feedback_enabled:
            feedback.stop_cue()
        path: Optional[Path] = None
        if self.save and rec.duration_s > 0:
            self.out_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
            path = self.out_dir / f"utterance-{stamp}.wav"
            save_wav(rec, str(path))
        self.last_recording = rec
        self.last_path = path
        msg = f"{rec.duration_s:.1f}s, peak {rec.peak}" + (f" → {path.name}" if path else "")
        print(f"[flowlinux] captured {msg}")
        if self.feedback_enabled:
            feedback.notify("FlowLinux", f"Captured {msg}")
        if self.on_utterance is not None:
            try:
                self.on_utterance(rec, path)
            except Exception as e:
                print(f"[flowlinux] on_utterance handler error: {e}")
        if self.once:
            self._done.set()

    # --- lifecycle ---
    def run(self) -> None:
        self.hotkey.start()
        hint = {
            PTTMode.HOLD: f"Hold [{self.key}] to talk, release to stop.",
            PTTMode.TOGGLE: f"Press [{self.key}] to start/stop.",
            PTTMode.DOUBLE_TAP: f"Double-tap [{self.key}] to start, press to stop.",
        }[self.mode]
        print(f"[flowlinux] recorder ready — {hint}  (Ctrl+C to quit)")
        try:
            while not self._done.is_set():
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n[flowlinux] stopping.")
        finally:
            self.stop()

    def stop(self) -> None:
        try:
            if self.recorder.is_recording:
                self.recorder.stop()
        finally:
            self.hotkey.stop()
