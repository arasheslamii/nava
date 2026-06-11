"""Formatter interface and result type (M4)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class FormatResult:
    text: str
    raw: str
    changed: bool = False
    notes: list[str] = field(default_factory=list)


class Formatter(ABC):
    @abstractmethod
    def format(self, text: str) -> FormatResult:
        """Return polished text. Must not raise; return the input unchanged on trouble."""
