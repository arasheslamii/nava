"""First-run setup wizard and config editor (Rich + questionary)."""

from __future__ import annotations

from pathlib import Path

from ..core.config import Config, default_dictionary_path

MODEL_CHOICES = {
    "small.en — balanced, recommended": "small.en",
    "base.en — fastest, lower accuracy": "base.en",
    "medium.en — most accurate, slow on CPU": "medium.en",
}
KEY_CHOICES = {
    "Right-Ctrl (ctrl_r) — recommended": "ctrl_r",
    "Right-Alt (alt_r)": "alt_r",
    "F12": "f12",
    "Pause": "pause",
}


def apply_answers(cfg: Config, answers: dict) -> Config:
    """Pure: map collected answers onto a Config (testable, no I/O)."""
    cfg.asr.model = answers["model"]
    cfg.hotkey.key = answers["key"]
    cfg.hotkey.mode = answers["mode"]
    cfg.formatting.enabled = answers["formatting"]
    cfg.feedback.cues = answers["cues"]
    cfg.cloud.enabled = answers["cloud"]
    return cfg


def _label_for(mapping: dict, value: str) -> str:
    for label, v in mapping.items():
        if v == value:
            return label
    return next(iter(mapping))


def _prompt(current: Config) -> dict | None:
    import questionary

    model = questionary.select("ASR model", choices=list(MODEL_CHOICES),
                               default=_label_for(MODEL_CHOICES, current.asr.model)).ask()
    if model is None:
        return None
    key = questionary.select("Push-to-talk key", choices=list(KEY_CHOICES),
                             default=_label_for(KEY_CHOICES, current.hotkey.key)).ask()
    mode = questionary.select("PTT mode", choices=["hold", "toggle", "double_tap"],
                              default=current.hotkey.mode).ask()
    formatting = questionary.confirm(
        "Enable Tier-1 formatting (filler removal + custom dictionary)?",
        default=current.formatting.enabled).ask()
    cues = questionary.select(
        "Feedback cues",
        choices=["off (silent, recommended)", "sound-only (one quiet beep)", "full (beeps + notifications)"],
        default={"off": "off (silent, recommended)",
                 "sound-only": "sound-only (one quiet beep)",
                 "full": "full (beeps + notifications)"}.get(current.feedback.cues,
                                                             "off (silent, recommended)")).ask()
    cloud = questionary.confirm("Enable cloud backends? (opt-in, off by default)",
                                default=current.cloud.enabled).ask()
    if None in (key, mode, formatting, cues, cloud):
        return None
    cues = cues.split()[0]  # "off" | "sound-only" | "full"
    return {"model": MODEL_CHOICES[model], "key": KEY_CHOICES[key], "mode": mode,
            "formatting": formatting, "cues": cues, "cloud": cloud}


def _seed_dictionary(console) -> None:
    dst = default_dictionary_path()
    if dst.exists():
        return
    example = Path(__file__).resolve().parents[2] / "config" / "dictionary.example.toml"
    if example.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        console.print(f"[green]Seeded custom dictionary → {dst}[/] (edit to add your terms)")


def run_setup() -> int:
    from rich.console import Console

    from .banner import print_banner
    from .diagnostics import render_diagnostics

    console = Console()
    print_banner(console)
    console.rule("[bold]Environment & dependencies")
    render_diagnostics(console)
    console.rule("[bold]Configure")
    answers = _prompt(Config.load())
    if answers is None:
        console.print("[yellow]Setup cancelled.[/]")
        return 1
    cfg = apply_answers(Config.load(), answers)
    path = cfg.save()
    console.print(f"[green]✓ Saved config → {path}[/]")
    _seed_dictionary(console)
    console.rule("[bold]Next steps")
    console.print("  • Try it now:        [cyan]flowlinux dictate[/]  (hold Right-Ctrl, speak)")
    console.print("  • Run as a service:  [cyan]flowlinux start[/]   (foreground)  / install systemd unit")
    console.print("  • Re-check anytime:  [cyan]flowlinux doctor[/]")
    return 0


def run_config_editor() -> int:
    from rich.console import Console

    console = Console()
    cfg = Config.load()
    console.rule("[bold]Edit FlowLinux config")
    answers = _prompt(cfg)
    if answers is None:
        console.print("[yellow]No changes saved.[/]")
        return 1
    path = apply_answers(cfg, answers).save()
    console.print(f"[green]✓ Saved → {path}[/]")
    return 0
