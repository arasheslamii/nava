"""Dependency preflight — detect missing system tools and produce an apt hint."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass


@dataclass
class Dependency:
    name: str       # binary name on PATH
    package: str    # apt package providing it
    required: bool
    purpose: str


DEPENDENCIES: list[Dependency] = [
    Dependency("xdotool", "xdotool", True,
               "XTEST typing + paste synthesis + active-window detection"),
    Dependency("xclip", "xclip", True,
               "clipboard read/write for the paste backend"),
    Dependency("xprop", "x11-utils", False,
               "read active-window WM_CLASS for per-app paste policy (terminals)"),
    Dependency("notify-send", "libnotify-bin", False,
               "desktop notification for the last-resort fallback"),
]


def check_dependencies() -> list[tuple[Dependency, bool]]:
    return [(d, shutil.which(d.name) is not None) for d in DEPENDENCIES]


def missing_required() -> list[Dependency]:
    return [d for d, ok in check_dependencies() if d.required and not ok]


def session_is_x11() -> bool:
    if os.environ.get("XDG_SESSION_TYPE", "").lower() == "x11":
        return True
    return bool(os.environ.get("DISPLAY")) and not os.environ.get("WAYLAND_DISPLAY")


def apt_install_hint(deps: list[Dependency]) -> str:
    pkgs = " ".join(sorted({d.package for d in deps}))
    return f"sudo apt-get install -y {pkgs}"
