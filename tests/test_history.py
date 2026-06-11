"""Last-transcript persistence (paste-last) tests."""

from __future__ import annotations

from nava.core import history


def test_save_load_clear(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    assert history.load_last() is None
    history.save_last("send it Wednesday")
    assert history.load_last() == "send it Wednesday"
    history.save_last("overwritten")  # only the latest is kept
    assert history.load_last() == "overwritten"
    history.clear_last()
    assert history.load_last() is None


def test_empty_string_reads_as_none(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    history.save_last("")
    assert history.load_last() is None
