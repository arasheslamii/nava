"""InjectionManager — backend selection with health checks and escalation."""

from __future__ import annotations

from .base import HealthStatus, InjectionResult, Injector
from .clipboard import ClipboardInjector
from .notify import NotifyInjector
from .xdotool import XdotoolInjector

# Above this length, prefer the (instant, Unicode-safe) paste path over per-char typing.
_AUTO_TYPE_MAX_LEN = 40


def prefer_paste(text: str) -> bool:
    """Heuristic for `auto`: route to clipboard-paste instead of XTEST typing.

    XTEST typing drops uncommon Unicode (e.g. U+2713 ✓ was lost in LibreOffice during M1
    acceptance) and is slow per-character on long text. Paste is instant and Unicode-safe,
    so we only type short, pure-ASCII strings (where typing feels native and is reliable).
    """
    if "\n" in text or len(text) > _AUTO_TYPE_MAX_LEN:
        return True
    return any(ord(ch) > 0x7F for ch in text)


class InjectionManager:
    """Pick a backend and escalate on failure.

    `auto` chooses paste-first for non-trivial/Unicode text (reliable, instant) and
    type-first for short ASCII (feels native); explicit `type`/`paste` force the order.
    A notify fallback never loses text.
    """

    def __init__(self, delay_ms: int = 12, restore_clipboard: bool = True):
        self.type_backend = XdotoolInjector(delay_ms=delay_ms)
        self.paste_backend = ClipboardInjector(restore=restore_clipboard)
        self.notify_backend = NotifyInjector()

    def backends_for(self, method: str, text: str = "") -> list[Injector]:
        type_first = [self.type_backend, self.paste_backend, self.notify_backend]
        paste_first = [self.paste_backend, self.type_backend, self.notify_backend]
        if method == "type":
            return type_first
        if method == "paste":
            return paste_first
        if method == "auto":
            return paste_first if prefer_paste(text) else type_first
        raise ValueError(f"unknown method: {method!r}")

    def health(self) -> list[HealthStatus]:
        return [b.health() for b in
                (self.type_backend, self.paste_backend, self.notify_backend)]

    def inject(self, text: str, method: str = "auto") -> InjectionResult:
        tried: list[str] = []
        last: InjectionResult | None = None
        for backend in self.backends_for(method, text):
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
