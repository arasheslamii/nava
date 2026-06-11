"""NotifyInjector — last-resort fallback that never loses the text."""

from __future__ import annotations

import shutil
import subprocess

from .base import Backend, HealthStatus, InjectionResult, Injector


class NotifyInjector(Injector):
    """Copy the text to the clipboard and tell the user via a desktop notification.

    Does not inject into the focused app, but guarantees the transcript is recoverable
    when every real backend fails.
    """

    name = Backend.NOTIFY.value

    def health(self) -> HealthStatus:
        # Always "available": worst case we just can't show a notification.
        return HealthStatus(self.name, True, "notify fallback always available")

    def inject(self, text: str) -> InjectionResult:
        copied = False
        if shutil.which("xclip"):
            try:
                p = subprocess.run(["xclip", "-selection", "clipboard", "-i"],
                                   input=text.encode("utf-8"), stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, timeout=2)
                copied = p.returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                copied = False
        msg = ("Transcript copied to clipboard — press paste."
               if copied else "Could not inject or copy text.")
        if shutil.which("notify-send"):
            try:
                subprocess.run(["notify-send", "-a", "NAVA", "NAVA", msg],
                               capture_output=True, timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                pass
        return InjectionResult(copied, self.name, text, msg)
