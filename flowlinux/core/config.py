"""FlowLinux configuration — TOML at ~/.config/flowlinux/config.toml.

Hand-editable; the `flowlinux config` TUI edits the same file. Nested dataclasses map to
TOML tables. Loading is tolerant: unknown keys are ignored, missing keys take defaults.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "flowlinux"


def default_config_path() -> Path:
    return config_dir() / "config.toml"


def default_dictionary_path() -> Path:
    return config_dir() / "dictionary.toml"


@dataclass
class ASRConfig:
    model: str = "small.en"
    device: str = "cpu"          # cpu | cuda | auto
    compute_type: str = "int8"
    vad: bool = True


@dataclass
class HotkeyConfig:
    key: str = "ctrl_r"          # Right-Ctrl
    mode: str = "hold"           # hold | toggle | double_tap


@dataclass
class InjectionConfig:
    method: str = "auto"         # auto | type | paste


@dataclass
class FormattingConfig:
    enabled: bool = True
    dictionary: str = str(default_dictionary_path())


@dataclass
class AudioConfig:
    device: str = ""             # "" = auto (pulse/pipewire)


@dataclass
class FeedbackConfig:
    sound: bool = True
    notify: bool = True


@dataclass
class CloudConfig:
    enabled: bool = False        # opt-in (ADR-0004)


@dataclass
class Config:
    asr: ASRConfig = field(default_factory=ASRConfig)
    hotkey: HotkeyConfig = field(default_factory=HotkeyConfig)
    injection: InjectionConfig = field(default_factory=InjectionConfig)
    formatting: FormattingConfig = field(default_factory=FormattingConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    feedback: FeedbackConfig = field(default_factory=FeedbackConfig)
    cloud: CloudConfig = field(default_factory=CloudConfig)

    _SECTIONS = {
        "asr": ASRConfig, "hotkey": HotkeyConfig, "injection": InjectionConfig,
        "formatting": FormattingConfig, "audio": AudioConfig,
        "feedback": FeedbackConfig, "cloud": CloudConfig,
    }

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        kwargs = {}
        for name, klass in cls._SECTIONS.items():
            section = data.get(name, {}) or {}
            fields = klass.__dataclass_fields__
            kwargs[name] = klass(**{k: v for k, v in section.items() if k in fields})
        return cls(**kwargs)

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Config":
        p = Path(path) if path else default_config_path()
        if not p.exists():
            return cls()
        import tomllib
        return cls.from_dict(tomllib.loads(p.read_text(encoding="utf-8")))

    def to_dict(self) -> dict:
        return {name: asdict(getattr(self, name)) for name in self._SECTIONS}

    def save(self, path: str | Path | None = None) -> Path:
        import tomli_w
        p = Path(path) if path else default_config_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(tomli_w.dumps(self.to_dict()), encoding="utf-8")
        return p

    @staticmethod
    def exists(path: str | Path | None = None) -> bool:
        p = Path(path) if path else default_config_path()
        return p.exists()
