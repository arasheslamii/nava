"""DictationApp (M3): hold key -> record -> transcribe -> inject. The product MVP."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from ..asr.base import ASRBackend
from ..audio import feedback
from ..audio.capture import Recording
from ..format.base import Formatter
from ..hotkey.base import PTTMode
from ..injection.manager import InjectionManager
from .recorder_app import RecorderApp


class DictationApp:
    def __init__(
        self,
        backend: ASRBackend,
        mode: PTTMode = PTTMode.HOLD,
        key: str = "ctrl_r",
        device=None,
        inject: bool = True,
        method: str = "auto",
        cues: str = "off",
        save_audio: bool = False,
        once: bool = False,
        formatter: Formatter | None = None,
    ):
        self.backend = backend
        self.injector = InjectionManager()
        self.inject = inject
        self.method = method
        self.formatter = formatter
        self.cues = cues
        self.recorder_app = RecorderApp(
            mode=mode, key=key, device=device, cues=cues,
            save=save_audio, once=once, on_utterance=self._on_utterance,
        )

    def warmup(self) -> None:
        self.backend.load()

    def _on_utterance(self, rec: Recording, path: Optional[Path]) -> None:
        if rec.duration_s < 0.2:
            return
        result = self.backend.transcribe(rec.audio, rec.sample_rate)
        text = result.text
        print(f"[asr] {result.duration_s:.1f}s audio, {result.infer_s:.2f}s infer "
              f"(rtf {result.rtf:.2f}), dropped {result.dropped} → {text!r}")
        if text and self.formatter is not None:
            fr = self.formatter.format(text)
            if fr.changed:
                print(f"[fmt] {', '.join(fr.notes) or 'cleaned'} → {fr.text!r}")
            text = fr.text
        if not text:
            if self.cues == "full":
                feedback.notify("NAVA", "(no speech detected)")
            return
        if not self.inject:
            return
        res = self.injector.inject(text, method=self.method)
        if not res.ok:
            print(f"[inject] FAILED: {res.detail}")
            if self.cues == "full":
                feedback.notify("NAVA", f"inject failed: {res.detail}")

    def run(self) -> None:
        print(f"[nava] loading model {self.backend.name} …")
        t0 = time.monotonic()
        self.warmup()
        print(f"[nava] model ready in {time.monotonic() - t0:.1f}s")
        self.recorder_app.run()
