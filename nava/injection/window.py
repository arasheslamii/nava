"""Active-window detection and per-app paste policy (X11)."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass

# Lowercased WM_CLASS tokens (res_name OR res_class) of terminals where Ctrl+V is
# consumed by the shell and paste must use Ctrl+Shift+V instead.
TERMINAL_WM_CLASSES: set[str] = {
    "gnome-terminal-server", "gnome-terminal", "konsole", "xterm", "uxterm",
    "urxvt", "rxvt", "st", "st-256color", "alacritty", "kitty", "terminator",
    "xfce4-terminal", "tilix", "termite", "qterminal", "lxterminal",
    "mate-terminal", "guake", "yakuake", "wezterm", "foot", "cool-retro-term",
    "deepin-terminal", "sakura", "roxterm",
}

_WM_CLASS_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')


@dataclass
class ActiveWindow:
    window_id: str
    wm_class: str  # primary identity (res_class, or res_name fallback), lowercased
    is_terminal: bool


def _run(cmd: list[str], timeout: float = 2.0) -> str | None:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def _wm_class(window_id: str) -> tuple[str, str]:
    """Return (res_name, res_class) lowercased via xprop.

    Note: `xdotool getwindowclassname` does not exist in older xdotool (e.g. 3.2016*),
    so we read the WM_CLASS property with xprop instead.
    """
    if not shutil.which("xprop"):
        return ("", "")
    out = _run(["xprop", "-id", window_id, "WM_CLASS"])
    if not out or "=" not in out:
        return ("", "")
    # Format: WM_CLASS(STRING) = "res_name", "res_class"
    tokens = _WM_CLASS_RE.findall(out.split("=", 1)[1])
    name = tokens[0].lower() if len(tokens) >= 1 else ""
    cls = tokens[1].lower() if len(tokens) >= 2 else ""
    return (name, cls)


def get_active_window() -> ActiveWindow | None:
    """Return the focused window's id/class, or None if it can't be determined."""
    if not shutil.which("xdotool"):
        return None
    wid = _run(["xdotool", "getactivewindow"])
    if not wid:
        return None
    res_name, res_class = _wm_class(wid)
    primary = res_class or res_name  # res_class is the conventional "class"
    is_terminal = res_class in TERMINAL_WM_CLASSES or res_name in TERMINAL_WM_CLASSES
    return ActiveWindow(window_id=wid, wm_class=primary, is_terminal=is_terminal)


def paste_keystroke_for(win: ActiveWindow | None) -> str:
    """xdotool key spec for paste in the focused app."""
    if win is not None and win.is_terminal:
        return "ctrl+shift+v"
    return "ctrl+v"
