"""Last-transcript persistence for the paste-last-transcript fallback.

Stores only the most recent transcript (overwritten each time) at
~/.cache/nava/last_transcript.txt so `nava paste-last` can re-inject it from a
separate process. Audio is never written here. Gate via [history] keep_last in config.
"""

from __future__ import annotations

import os
from pathlib import Path


def cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return Path(base) / "nava"


def last_transcript_path() -> Path:
    return cache_dir() / "last_transcript.txt"


def save_last(text: str) -> None:
    p = last_transcript_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def load_last() -> str | None:
    p = last_transcript_path()
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8")
    return text or None


def clear_last() -> None:
    last_transcript_path().unlink(missing_ok=True)
