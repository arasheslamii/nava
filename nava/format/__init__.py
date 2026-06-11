"""Formatting layer (M4).

Tier-1 (default, offline, ~0 ms): custom dictionary (proper-noun correction) + rule
cleanup (fillers, spacing, capitalization, terminal punctuation). Tier-2 cloud LLM and
Tier-3 local LLM (OFF on this box) slot in behind the same `Formatter` interface later.
"""

from .base import FormatResult, Formatter
from .dictionary import CustomDictionary
from .pipeline import FormatterPipeline, build_pipeline, default_dictionary_path
from .rules import Tier1RuleFormatter

__all__ = [
    "Formatter", "FormatResult", "CustomDictionary", "Tier1RuleFormatter",
    "FormatterPipeline", "build_pipeline", "default_dictionary_path",
]
