"""InjectionManager — backend selection with health checks and escalation."""

from __future__ import annotations

from .base import HealthStatus, InjectionResult, Injector
from .clipboard import ClipboardInjector
from .notify import NotifyInjector
from .xdotool import XdotoolInjector


class InjectionManager:
    """Pick a backend and escalate on failure: type -> paste -> notify.

    On X11 the primary is XTEST typing (feels native); clipboard-paste handles big or
    Unicode-heavy text and apps where typing is unreliable; notify never loses text.
    """

    def __init__(self, delay_ms: int = 12, restore_clipboard: bool = True):
        self.type_backend = XdotoolInjector(delay_ms=delay_ms)
        self.paste_backend = ClipboardInjector(restore=restore_clipboard)
        self.notify_backend = NotifyInjector()

    def backends_for(self, method: str) -> list[Injector]:
        if method in ("auto", "type"):
            return [self.type_backend, self.paste_backend, self.notify_backend]
        if method == "paste":
            return [self.paste_backend, self.type_backend, self.notify_backend]
        raise ValueError(f"unknown method: {method!r}")

    def health(self) -> list[HealthStatus]:
        return [b.health() for b in
                (self.type_backend, self.paste_backend, self.notify_backend)]

    def inject(self, text: str, method: str = "auto") -> InjectionResult:
        tried: list[str] = []
        last: InjectionResult | None = None
        for backend in self.backends_for(method):
            h = backend.health()
            if not h.ok:
                tried.append(f"{backend.name}(unhealthy:{h.detail})")
                continue
            res = backend.inject(text)
            if res.ok:
                res.fallbacks = tried
                return res
            tried.append(f"{backend.name}(failed:{res.detail})")
            last = res
        detail = last.detail if last else "no usable injection backend"
        return InjectionResult(False, "none", text, detail, fallbacks=tried)
