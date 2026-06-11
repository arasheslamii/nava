"""systemd --user service helpers for the headless background daemon (ADR-0007).

The unit's ExecStart runs the foreground daemon (`flowlinux _run`). `flowlinux start`
installs the unit on demand and starts it, so the daemon survives the terminal closing.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

SERVICE = "flowlinux.service"


def have_systemd() -> bool:
    return shutil.which("systemctl") is not None


def _systemctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["systemctl", "--user", *args], capture_output=True, text=True)


def unit_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "systemd" / "user" / SERVICE


def _unit_contents() -> str:
    # Run via the interpreter that owns this install, so it works regardless of PATH.
    exec_start = f"{sys.executable} -m flowlinux.cli_main _run"
    env = [f"Environment=DISPLAY={os.environ.get('DISPLAY', ':0')}"]
    if os.environ.get("XAUTHORITY"):
        env.append(f"Environment=XAUTHORITY={os.environ['XAUTHORITY']}")
    return (
        "[Unit]\n"
        "Description=FlowLinux voice dictation daemon\n"
        "After=graphical-session.target\n"
        "PartOf=graphical-session.target\n\n"
        "[Service]\n"
        "Type=simple\n"
        f"ExecStart={exec_start}\n"
        "Restart=on-failure\n"
        "RestartSec=3\n"
        + "\n".join(env) + "\n\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )


def is_installed() -> bool:
    return unit_path().exists()


def install_unit() -> Path:
    p = unit_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_unit_contents(), encoding="utf-8")
    if have_systemd():
        _systemctl("daemon-reload")
    return p


def ensure_installed() -> None:
    if not is_installed():
        install_unit()


def is_active() -> bool:
    return have_systemd() and _systemctl("is-active", SERVICE).stdout.strip() == "active"


def main_pid() -> int | None:
    if not have_systemd():
        return None
    out = _systemctl("show", SERVICE, "-p", "MainPID", "--value").stdout.strip()
    return int(out) if out.isdigit() and out != "0" else None


def start() -> tuple[bool, str]:
    if not have_systemd():
        return False, "systemd --user unavailable; run `flowlinux _run` in the foreground"
    ensure_installed()
    r = _systemctl("start", SERVICE)
    if r.returncode != 0:
        return False, (r.stderr.strip() or "systemctl start failed")
    pid = main_pid()
    return True, f"running in background{f' (PID {pid})' if pid else ''}"


def stop() -> tuple[bool, str]:
    if not have_systemd():
        return False, "systemd --user unavailable"
    if not is_installed():
        return False, "service not installed (nothing to stop)"
    r = _systemctl("stop", SERVICE)
    return r.returncode == 0, (r.stderr.strip() or "stopped")


def enable() -> tuple[bool, str]:
    if not have_systemd():
        return False, "systemd --user unavailable"
    ensure_installed()
    r = _systemctl("enable", "--now", SERVICE)
    if r.returncode != 0:
        return False, (r.stderr.strip() or "systemctl enable failed")
    return True, "enabled (auto-start on login) and started"


def status_text() -> str:
    if not have_systemd():
        return "systemd not available (use `flowlinux _run` to test in the foreground)"
    if not is_installed():
        return "not installed (run `flowlinux start` to install + launch)"
    if is_active():
        pid = main_pid()
        return f"running in background (PID {pid})" if pid else "running in background"
    return "installed but stopped"
