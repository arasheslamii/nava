"""FormatterPipeline — dictionary correction then Tier-1 rules (M4)."""

from __future__ import annotations

import os
from pathlib import Path

from .base import FormatResult, Formatter
from .dictionary import CustomDictionary
from .rules import Tier1RuleFormatter


class FormatterPipeline(Formatter):
    """Apply the custom dictionary (correct proper nouns) first, then rule cleanup."""

    def __init__(
        self,
        dictionary: CustomDictionary | None = None,
        rules: Tier1RuleFormatter | None = None,
        enabled: bool = True,
    ):
        self.dictionary = dictionary or CustomDictionary()
        self.rules = rules or Tier1RuleFormatter()
        self.enabled = enabled

    def format(self, text: str) -> FormatResult:
        raw = text
        if not self.enabled:
            return FormatResult(text=text, raw=raw, changed=False, notes=["formatting disabled"])
        corrected, dict_notes = self.dictionary.apply(text)
        res = self.rules.format(corrected)
        notes = [f"dict {n}" for n in dict_notes] + res.notes
        return FormatResult(text=res.text, raw=raw, changed=(res.text != raw), notes=notes)


def default_dictionary_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "flowlinux" / "dictionary.toml"


def build_pipeline(dict_path: str | None = None, enabled: bool = True) -> FormatterPipeline:
    """Load the custom dictionary from `dict_path` (or the user config default if present)."""
    path = Path(dict_path) if dict_path else default_dictionary_path()
    dictionary = CustomDictionary.from_file(path) if path.exists() else CustomDictionary()
    return FormatterPipeline(dictionary=dictionary, enabled=enabled)
