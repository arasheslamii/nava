"""Unit + light integration tests for the M1 injection layer."""

from __future__ import annotations

import os
import shutil

import pytest

from flowlinux.injection.base import HealthStatus, InjectionResult, Injector
from flowlinux.injection.manager import InjectionManager
from flowlinux.injection.window import (
    TERMINAL_WM_CLASSES,
    ActiveWindow,
    paste_keystroke_for,
)


# --- per-app paste policy ---

def test_terminal_uses_ctrl_shift_v():
    term = ActiveWindow("1", "gnome-terminal-server", True)
    assert paste_keystroke_for(term) == "ctrl+shift+v"


def test_non_terminal_uses_ctrl_v():
    assert paste_keystroke_for(ActiveWindow("2", "firefox", False)) == "ctrl+v"
    assert paste_keystroke_for(None) == "ctrl+v"


def test_common_terminals_classified():
    for cls in ("gnome-terminal-server", "konsole", "alacritty", "kitty", "xterm"):
        assert cls in TERMINAL_WM_CLASSES


# --- manager escalation logic (with fakes, no X server needed) ---

class _Fake(Injector):
    def __init__(self, name, healthy, succeed):
        self.name = name
        self._healthy = healthy
        self._succeed = succeed
        self.calls = 0

    def health(self):
        return HealthStatus(self.name, self._healthy, "fake")

    def inject(self, text):
        self.calls += 1
        return InjectionResult(self._succeed, self.name, text, "fake")


def _wire(mgr, type_b, paste_b, notify_b):
    mgr.type_backend, mgr.paste_backend, mgr.notify_backend = type_b, paste_b, notify_b


def test_escalates_past_healthy_failure_to_next_success():
    mgr = InjectionManager()
    t = _Fake("type", True, False)    # healthy but fails
    p = _Fake("paste", True, True)    # succeeds
    n = _Fake("notify", True, True)
    _wire(mgr, t, p, n)
    res = mgr.inject("hi", method="auto")
    assert res.ok and res.backend == "paste"
    assert t.calls == 1 and p.calls == 1 and n.calls == 0
    assert any("type" in f for f in res.fallbacks)


def test_skips_unhealthy_backend_without_calling_it():
    mgr = InjectionManager()
    t = _Fake("type", False, True)    # unhealthy -> never called
    p = _Fake("paste", True, True)
    n = _Fake("notify", True, True)
    _wire(mgr, t, p, n)
    res = mgr.inject("hi", method="auto")
    assert res.ok and res.backend == "paste"
    assert t.calls == 0


def test_paste_method_orders_paste_first():
    mgr = InjectionManager()
    t = _Fake("type", True, True)
    p = _Fake("paste", True, True)
    n = _Fake("notify", True, True)
    _wire(mgr, t, p, n)
    res = mgr.inject("hi", method="paste")
    assert res.backend == "paste" and t.calls == 0


def test_all_fail_returns_none_backend():
    mgr = InjectionManager()
    _wire(mgr, _Fake("type", True, False), _Fake("paste", True, False),
          _Fake("notify", True, False))
    res = mgr.inject("hi", method="auto")
    assert not res.ok and res.backend == "none"


# --- real clipboard round-trip (needs X11 + xclip) ---

@pytest.mark.skipif(
    not (os.environ.get("DISPLAY") and shutil.which("xclip")),
    reason="needs an X11 display and xclip",
)
def test_clipboard_roundtrip_with_unicode():
    from flowlinux.injection.clipboard import ClipboardInjector

    ci = ClipboardInjector()
    marker = "flowlinux-test-éè—\U0001f600-42"  # accents, em-dash, emoji
    assert ci._set_clipboard(marker.encode("utf-8"))
    got = ci._get_clipboard()
    assert got is not None and got.decode("utf-8") == marker
