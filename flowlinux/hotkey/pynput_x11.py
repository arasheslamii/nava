"""X11 global key listener (pynput) feeding the PTTController.

Monitors (does not grab) a single modifier key for push-to-talk. OS key auto-repeat
(repeated KeyPress while held) is collapsed into one down/up edge pair.
"""

from __future__ import annotations

from .base import PTTController

# Friendly aliases -> pynput Key.name
KEY_ALIASES = {
    "right_ctrl": "ctrl_r", "rctrl": "ctrl_r", "ctrl_r": "ctrl_r",
    "left_ctrl": "ctrl_l", "lctrl": "ctrl_l", "ctrl_l": "ctrl_l",
    "right_alt": "alt_r", "ralt": "alt_r", "alt_r": "alt_r", "alt_gr": "alt_gr",
    "right_shift": "shift_r", "shift_r": "shift_r",
    "right_super": "cmd_r", "super_r": "cmd_r", "cmd_r": "cmd_r",
    "pause": "pause", "scroll_lock": "scroll_lock", "f12": "f12",
}


def normalize_key(name: str) -> str:
    return KEY_ALIASES.get(name.strip().lower(), name.strip().lower())


class PynputX11Hotkey:
    def __init__(self, controller: PTTController, key: str = "ctrl_r"):
        self.controller = controller
        self.key_name = normalize_key(key)
        self._down = False
        self._listener = None

    def _matches(self, key) -> bool:
        name = getattr(key, "name", None)  # pynput Key has .name; KeyCode does not
        if name is not None:
            return name == self.key_name
        # bare character key (KeyCode) — match against its char if someone binds a letter
        ch = getattr(key, "char", None)
        return ch is not None and ch == self.key_name

    def _on_press(self, key) -> None:
        if self._matches(key) and not self._down:  # ignore auto-repeat
            self._down = True
            self.controller.key_down()

    def _on_release(self, key) -> None:
        if self._matches(key) and self._down:
            self._down = False
            self.controller.key_up()

    def start(self) -> None:
        from pynput import keyboard  # imported lazily (needs DISPLAY)
        self._listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        )
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def join(self) -> None:
        if self._listener is not None:
            self._listener.join()
