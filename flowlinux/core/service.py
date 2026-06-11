"""systemd --user service helpers for the headless daemon (ADR-0007)."""

from __future__ import annotations

import shutil
import subprocess

SERVICE = "flowlinux.service"


def have_systemd() -> bool:
    return shutil.which("systemctl") is not None


def _systemctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["systemctl", "--user", *args], capture_output=True, text=True)


def is_active() -> bool:
    if not have_systemd():
        return False
    return _systemctl("is-active", SERVICE).stdout.strip() == "active"


def is_installed() -> bool:
    if not have_systemd():
        return False
    r = _systemctl("list-unit-files", SERVICE)
    return SERVICE in r.stdout


def start() -> tuple[bool, str]:
    if not is_installed():
        return False, "service not installed (run the installer / `flowlinux setup`)"
    r = _systemctl("start", SERVICE)
    return r.returncode == 0, (r.stderr.strip() or "started")


def stop() -> tuple[bool, str]:
    if not is_installed():
        return False, "service not installed"
    r = _systemctl("stop", SERVICE)
    return r.returncode == 0, (r.stderr.strip() or "stopped")


def status_text() -> str:
    if not have_systemd():
        return "systemd not available (run `flowlinux start` in the foreground)"
    if not is_installed():
        return "not installed as a service (run `flowlinux setup`, or `flowlinux start` foreground)"
    return "active (running)" if is_active() else "installed but stopped"
