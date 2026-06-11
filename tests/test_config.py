"""Config round-trip + wizard answer-mapping tests."""

from __future__ import annotations

from nava.core.config import Config
from nava.tui.wizard import apply_answers


def test_defaults():
    c = Config()
    assert c.asr.model == "small.en" and c.asr.device == "cpu"
    assert c.hotkey.key == "ctrl_r" and c.hotkey.mode == "hold"
    assert c.formatting.enabled is True
    assert c.cloud.enabled is False


def test_from_dict_is_tolerant():
    c = Config.from_dict({
        "asr": {"model": "medium.en", "bogus": 1},   # unknown key ignored
        "hotkey": {"mode": "toggle"},                  # partial section -> defaults fill
        "nope": {"x": 1},                              # unknown section ignored
    })
    assert c.asr.model == "medium.en"
    assert c.hotkey.mode == "toggle" and c.hotkey.key == "ctrl_r"


def test_save_load_roundtrip(tmp_path):
    p = tmp_path / "config.toml"
    c = Config()
    c.asr.model = "base.en"
    c.hotkey.key = "f12"
    c.cloud.enabled = True
    c.save(p)
    assert p.exists()
    loaded = Config.load(p)
    assert loaded.asr.model == "base.en"
    assert loaded.hotkey.key == "f12"
    assert loaded.cloud.enabled is True


def test_load_missing_returns_defaults(tmp_path):
    assert Config.load(tmp_path / "absent.toml").asr.model == "small.en"


def test_apply_answers():
    c = apply_answers(Config(), {
        "model": "medium.en", "key": "alt_r", "mode": "double_tap",
        "formatting": False, "cues": "full", "cloud": True,
    })
    assert c.asr.model == "medium.en" and c.hotkey.key == "alt_r"
    assert c.hotkey.mode == "double_tap"
    assert c.formatting.enabled is False and c.feedback.cues == "full"
    assert c.cloud.enabled is True


def test_default_cues_is_off():
    assert Config().feedback.cues == "off"
