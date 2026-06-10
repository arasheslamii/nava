"""Injection backend interface and result types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class Backend(str, Enum):
    TYPE = "type"      # XTEST synthetic typing (xdotool)
    PASTE = "paste"    # clipboard set + synthesized paste (xclip + xdotool)
    NOTIFY = "notify"  # last resort: copy to clipboard + desktop notification
    WAYLAND = "wayland"  # future: wtype/ydotool/wl-copy (not implemented)


@dataclass
class HealthStatus:
    backend: str
    ok: bool
    detail: str = ""


@dataclass
class InjectionResult:
    ok: bool
    backend: str
    text: str
    detail: str = ""
    fallbacks: list[str] = field(default_factory=list)  # backends tried before this one


class Injector(ABC):
    """One text-injection backend. Cheap to construct; holds no per-text state."""

    name: str = "injector"

    @abstractmethod
    def health(self) -> HealthStatus:
        """Runtime check: are this backend's dependencies usable right now?"""

    @abstractmethod
    def inject(self, text: str) -> InjectionResult:
        """Deliver `text` to the focused window.

        Must not raise — return ``InjectionResult(ok=False, ...)`` on any failure so
        the manager can escalate to the next backend.
        """
