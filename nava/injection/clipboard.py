"""ClipboardInjector — clipboard set + synthesized paste, with save/restore."""

from __future__ import annotations

import os
import shutil
import subprocess
import time

from .base import Backend, HealthStatus, InjectionResult, Injector
from .window import get_active_window, paste_keystroke_for


class ClipboardInjector(Injector):
    """Save the clipboard, set it to our text, synthesize the app-appropriate paste
    keystroke (Ctrl+V / Ctrl+Shift+V in terminals), then restore the original.

    Best for large or Unicode-heavy text and apps where synthetic typing is slow or
    unreliable. The save/restore is best-effort and racy (the target app may read the
    clipboard asynchronously) — a short settle delay mitigates it. See DECISIONS.md.
    """

    name = Backend.PASTE.value

    def __init__(self, restore: bool = True, settle_s: float = 0.12):
        self.restore = restore
        self.settle_s = settle_s

    def health(self) -> HealthStatus:
        if not shutil.which("xclip"):
            return HealthStatus(self.name, False, "xclip not installed (apt install xclip)")
        if not shutil.which("xdotool"):
            return HealthStatus(self.name, False, "xdotool not installed (needed to paste)")
        if not os.environ.get("DISPLAY"):
            return HealthStatus(self.name, False, "no DISPLAY (X11 required)")
        return HealthStatus(self.name, True, "xclip + xdotool + DISPLAY present")

    # --- clipboard primitives ---
    def _get_clipboard(self) -> bytes | None:
        try:
            out = subprocess.run(["xclip", "-selection", "clipboard", "-o"],
                                 capture_output=True, timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            return None
        if out.returncode != 0:
            return None  # commonly means the clipboard is empty
        return out.stdout

    def _set_clipboard(self, data: bytes) -> bool:
        # `xclip -i` forks a background process to keep owning the selection; capturing
        # its stdout/stderr through a PIPE makes us block until that daemon exits (which
        # only happens when another app takes the clipboard). Redirect to DEVNULL so the
        # foreground process returns immediately.
        try:
            p = subprocess.run(["xclip", "-selection", "clipboard", "-i"],
                               input=data, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=2)
            return p.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    def inject(self, text: str) -> InjectionResult:
        if not text:
            return InjectionResult(True, self.name, text, "empty text, nothing to paste")
        h = self.health()
        if not h.ok:
            return InjectionResult(False, self.name, text, h.detail)

        saved = self._get_clipboard() if self.restore else None
        if not self._set_clipboard(text.encode("utf-8")):
            return InjectionResult(False, self.name, text, "failed to set clipboard")
        time.sleep(self.settle_s)  # let the new clipboard ownership propagate

        win = get_active_window()
        keys = paste_keystroke_for(win)
        try:
            p = subprocess.run(["xdotool", "key", "--clearmodifiers", keys],
                               capture_output=True, text=True, timeout=5)
            paste_ok = p.returncode == 0
            if paste_ok:
                where = f" into {win.wm_class}" if win else ""
                detail = f"pasted via {keys}{where}"
            else:
                detail = p.stderr.strip() or "xdotool key failed"
        except (OSError, subprocess.TimeoutExpired) as e:
            paste_ok, detail = False, f"xdotool key failed: {e}"

        if self.restore and saved is not None:
            time.sleep(self.settle_s)
            self._set_clipboard(saved)
            # If the clipboard was empty we leave our text in place (xclip can't easily
            # clear a selection); harmless.

        return InjectionResult(paste_ok, self.name, text, detail)
