"""Aggregate subsystem health checks (structured, UI-agnostic)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from ..injection.preflight import check_dependencies, session_is_x11


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    required: bool = True

    @property
    def status(self) -> str:
        return "ok" if self.ok else ("FAIL" if self.required else "absent")


def _audio_check() -> Check:
    try:
        import sounddevice as sd

        from ..audio.capture import resolve_input_device

        dev = resolve_input_device(None)
        info = (sd.query_devices(dev, "input") if dev is not None
                else sd.query_devices(kind="input"))
        return Check("microphone", True, f"{info['name']} ({int(info['default_samplerate'])} Hz)")
    except Exception as e:  # noqa: BLE001
        return Check("microphone", False, str(e))


def _hotkey_check() -> Check:
    if not os.environ.get("DISPLAY"):
        return Check("hotkey", False, "no DISPLAY (X11 required for pynput listener)")
    try:
        import pynput  # noqa: F401

        return Check("hotkey", True, "pynput available, X11 present")
    except Exception as e:  # noqa: BLE001
        return Check("hotkey", False, f"pynput import failed: {e}")


def _asr_check() -> Check:
    try:
        import faster_whisper  # noqa: F401

        return Check("asr (faster-whisper)", True, "import ok", required=False)
    except Exception as e:  # noqa: BLE001
        return Check("asr (faster-whisper)", False, str(e), required=False)


def run_all() -> list[Check]:
    x11 = session_is_x11()
    checks = [Check("session X11", x11,
                    "X11" if x11 else "not X11 — Wayland injector not built yet")]
    for dep, ok in check_dependencies():
        checks.append(Check(dep.name, ok, dep.purpose, required=dep.required))
    checks.append(_audio_check())
    checks.append(_hotkey_check())
    checks.append(_asr_check())
    return checks


def all_required_ok(checks: list[Check] | None = None) -> bool:
    checks = checks if checks is not None else run_all()
    return all(c.ok for c in checks if c.required)
