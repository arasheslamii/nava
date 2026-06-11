"""Push-to-talk state machine (pure logic — no OS deps, fully unit-testable)."""

from __future__ import annotations

import time
from enum import Enum
from typing import Callable


class PTTMode(str, Enum):
    HOLD = "hold"              # record while the key is held down (Wispr default)
    TOGGLE = "toggle"         # press to start, press again to stop
    DOUBLE_TAP = "double_tap"  # double-tap to start, single press to stop


class PTTController:
    """Translates debounced key-down/up edges + a mode into start/stop callbacks.

    The caller is responsible for collapsing OS key auto-repeat into single edges
    (the pynput listener does this). `now` is injectable for deterministic tests.
    """

    def __init__(
        self,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
        mode: PTTMode = PTTMode.HOLD,
        double_tap_window: float = 0.35,
    ):
        self.on_start = on_start
        self.on_stop = on_stop
        self.mode = PTTMode(mode)
        self.double_tap_window = double_tap_window
        self._active = False
        self._last_down = -1e9

    @property
    def active(self) -> bool:
        return self._active

    def key_down(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        if self.mode is PTTMode.HOLD:
            if not self._active:
                self._activate()
        elif self.mode is PTTMode.TOGGLE:
            self._deactivate() if self._active else self._activate()
        elif self.mode is PTTMode.DOUBLE_TAP:
            if self._active:
                self._deactivate()
            elif (now - self._last_down) <= self.double_tap_window:
                self._activate()
            self._last_down = now

    def key_up(self, now: float | None = None) -> None:
        if self.mode is PTTMode.HOLD and self._active:
            self._deactivate()

    def _activate(self) -> None:
        self._active = True
        self.on_start()

    def _deactivate(self) -> None:
        self._active = False
        self.on_stop()
