"""Custom dictionary — correct ASR mishears of jargon / proper nouns (Tier-1).

Keys are lowercase mishears; values are the exact replacement (case preserved). Matching
is case-insensitive and word-boundary aware, longest phrase first. This is the model-
independent fix for invented proper nouns no Whisper model knows (e.g. "MAAD Capital").
"""

from __future__ import annotations

import re
from pathlib import Path


class CustomDictionary:
    def __init__(self, corrections: dict[str, str] | None = None):
        self.corrections: dict[str, str] = {}
        for k, v in (corrections or {}).items():
            self.corrections[k.lower()] = v
        self._regex = self._compile()

    def _compile(self):
        if not self.corrections:
            return None
        # longest first so multi-word phrases win over their substrings
        keys = sorted(self.corrections, key=len, reverse=True)
        body = "|".join(re.escape(k) for k in keys)
        # word-boundary via lookarounds on word chars (handles multi-word phrases)
        return re.compile(rf"(?<!\w)(?:{body})(?!\w)", re.IGNORECASE)

    def apply(self, text: str) -> tuple[str, list[str]]:
        if not self._regex:
            return text, []
        notes: list[str] = []

        def repl(m: re.Match) -> str:
            src = m.group(0)
            dst = self.corrections[src.lower()]
            if src != dst:
                notes.append(f"{src!r}→{dst!r}")
            return dst

        return self._regex.sub(repl, text), notes

    @classmethod
    def from_file(cls, path: str | Path) -> "CustomDictionary":
        import tomllib

        data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
        corr = data.get("corrections", {})
        return cls({str(k): str(v) for k, v in corr.items()})
