"""Text-injection abstraction layer (M1).

On X11 the primary backend is XTEST synthetic typing (xdotool); clipboard-paste
handles large/Unicode text and apps where typing is unreliable; a notify fallback
guarantees text is never lost. A future WaylandInjector (wtype/ydotool/wl-copy)
slots in behind the same `Injector` interface.
"""

from .base import Backend, HealthStatus, InjectionResult, Injector
from .manager import InjectionManager

__all__ = [
    "Backend",
    "HealthStatus",
    "InjectionResult",
    "Injector",
    "InjectionManager",
]
