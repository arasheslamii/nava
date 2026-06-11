"""XdotoolInjector — XTEST synthetic typing via `xdotool type`."""

from __future__ import annotations

import os
import shutil
import subprocess

from .base import Backend, HealthStatus, InjectionResult, Injector


class XdotoolInjector(Injector):
    """Type `text` into the focused window using XTEST.

    Text is fed via stdin (``--file -``) rather than argv, so arbitrary Unicode,
    quotes, and shell metacharacters are handled without escaping headaches.
    """

    name = Backend.TYPE.value

    def __init__(self, delay_ms: int = 12):
        # xdotool's default inter-key delay is 12ms; 0 is faster but some apps drop keys.
        self.delay_ms = delay_ms

    def health(self) -> HealthStatus:
        if not shutil.which("xdotool"):
            return HealthStatus(self.name, False, "xdotool not installed (apt install xdotool)")
        if not os.environ.get("DISPLAY"):
            return HealthStatus(self.name, False, "no DISPLAY (X11 required for XTEST typing)")
        return HealthStatus(self.name, True, "xdotool + DISPLAY present")

    def inject(self, text: str) -> InjectionResult:
        if not text:
            return InjectionResult(True, self.name, text, "empty text, nothing to type")
        h = self.health()
        if not h.ok:
            return InjectionResult(False, self.name, text, h.detail)
        try:
            proc = subprocess.run(
                ["xdotool", "type", "--clearmodifiers", "--delay", str(self.delay_ms),
                 "--file", "-"],
                input=text, text=True, capture_output=True, timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            return InjectionResult(False, self.name, text, f"xdotool failed: {e}")
        if proc.returncode != 0:
            return InjectionResult(False, self.name, text,
                                   proc.stderr.strip() or "xdotool nonzero exit")
        return InjectionResult(True, self.name, text, "typed via XTEST")
