"""Tier-1 rule formatter — fillers, spacing, capitalization, terminal punctuation.

Deterministic, offline, ~0 ms. Whisper already capitalizes/punctuates, so this mostly
cleans up after filler removal and dictionary correction.
"""

from __future__ import annotations

import re

from .base import FormatResult, Formatter

# Conservative defaults: disfluencies that are virtually always fillers. Ambiguous words
# ("like", "actually", "basically") are intentionally NOT removed by default.
DEFAULT_FILLERS = ["um", "uh", "umm", "uhh", "uhm", "er", "erm", "hmm", "mm", "mhm"]
DEFAULT_FILLER_PHRASES = ["you know", "i mean", "sort of", "kind of"]


class Tier1RuleFormatter(Formatter):
    def __init__(
        self,
        fillers: list[str] | None = None,
        filler_phrases: list[str] | None = None,
        remove_fillers: bool = True,
        capitalize: bool = True,
        ensure_terminal_punct: bool = True,
    ):
        self.fillers = fillers if fillers is not None else DEFAULT_FILLERS
        self.filler_phrases = filler_phrases if filler_phrases is not None else DEFAULT_FILLER_PHRASES
        self.remove_fillers = remove_fillers
        self.capitalize = capitalize
        self.ensure_terminal_punct = ensure_terminal_punct
        toks = sorted(self.filler_phrases + self.fillers, key=len, reverse=True)
        self._filler_re = (
            re.compile(rf"(?<!\w)(?:{'|'.join(re.escape(t) for t in toks)})(?!\w),?\s*",
                       re.IGNORECASE)
            if toks else None
        )

    def format(self, text: str) -> FormatResult:
        raw = text
        s = text.strip()
        notes: list[str] = []

        if self.remove_fillers and self._filler_re:
            s2 = self._filler_re.sub("", s)
            if s2 != s:
                notes.append("removed fillers")
            s = s2

        s = re.sub(r"\s+", " ", s)               # collapse whitespace
        s = re.sub(r"\s+([,.!?;:])", r"\1", s)    # no space before punctuation
        s = s.strip(" ,")

        if self.capitalize:
            s = self._capitalize(s)
        if self.ensure_terminal_punct and s and s[-1] not in ".!?":
            s += "."
            notes.append("added terminal punctuation")

        return FormatResult(text=s, raw=raw, changed=(s != raw), notes=notes)

    @staticmethod
    def _capitalize(s: str) -> str:
        out = list(s)
        cap = True
        for i, ch in enumerate(s):
            if ch.isalpha():
                if cap:
                    out[i] = ch.upper()
                cap = False
            elif ch.isdigit():
                cap = False
            # sentence end only when followed by a space or end-of-string (not "3.30")
            if ch in ".!?" and (i + 1 >= len(s) or s[i + 1] == " "):
                cap = True
        result = "".join(out)
        return re.sub(r"\bi\b", "I", result)  # standalone "i" -> "I"
