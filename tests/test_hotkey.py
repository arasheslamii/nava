"""Unit tests for the push-to-talk state machine (no OS deps)."""

from __future__ import annotations

from nava.hotkey.base import PTTController, PTTMode
from nava.hotkey.pynput_x11 import normalize_key


class Spy:
    def __init__(self):
        self.starts = 0
        self.stops = 0

    def start(self):
        self.starts += 1

    def stop(self):
        self.stops += 1


def test_hold_starts_on_down_stops_on_up():
    s = Spy()
    c = PTTController(s.start, s.stop, mode=PTTMode.HOLD)
    c.key_down()
    assert c.active and s.starts == 1 and s.stops == 0
    c.key_up()
    assert not c.active and s.stops == 1


def test_hold_ignores_repeat_down_while_active():
    s = Spy()
    c = PTTController(s.start, s.stop, mode=PTTMode.HOLD)
    c.key_down()
    c.key_down()  # auto-repeat-style duplicate
    assert s.starts == 1
    c.key_up()
    assert s.stops == 1


def test_toggle_alternates_on_each_down():
    s = Spy()
    c = PTTController(s.start, s.stop, mode=PTTMode.TOGGLE)
    c.key_down(); assert c.active and s.starts == 1
    c.key_up()   ; assert c.active and s.stops == 0   # release is a no-op in toggle
    c.key_down() ; assert not c.active and s.stops == 1


def test_double_tap_requires_two_quick_taps_then_press_to_stop():
    s = Spy()
    c = PTTController(s.start, s.stop, mode=PTTMode.DOUBLE_TAP, double_tap_window=0.3)
    c.key_down(now=0.0)        # first tap, too far from previous -> no start
    assert not c.active and s.starts == 0
    c.key_down(now=0.2)        # second tap within window -> start
    assert c.active and s.starts == 1
    c.key_down(now=1.0)        # later single press -> stop
    assert not c.active and s.stops == 1


def test_double_tap_too_slow_does_not_start():
    s = Spy()
    c = PTTController(s.start, s.stop, mode=PTTMode.DOUBLE_TAP, double_tap_window=0.3)
    c.key_down(now=0.0)
    c.key_down(now=0.9)        # gap > window -> still no start
    assert not c.active and s.starts == 0


def test_key_aliases():
    assert normalize_key("Right-Ctrl".replace("-", "_")) == "ctrl_r"
    assert normalize_key("right_ctrl") == "ctrl_r"
    assert normalize_key("ctrl_r") == "ctrl_r"
    assert normalize_key("f12") == "f12"
