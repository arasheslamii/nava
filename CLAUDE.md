# CLAUDE.md — FlowLinux conventions & build/run

System-wide, local-first AI voice dictation for Linux. Clean-room implementation — no
code, assets, or branding copied from any other product.

## Target machine (dev/reference)
Linux Mint 22 (Ubuntu 24.04 base) · Cinnamon on **X11** · PipeWire · i7-4720HQ (Haswell,
4c/8t) · GTX 960M 4GB (Maxwell CC 5.0, driver 470 / CUDA 11.4) · 15 GiB RAM.
Full environment + rationale in [PLAN.md](PLAN.md).

## Architecture (locked — see DECISIONS.md)
- **All-Python core + terminal UI (Rich + questionary). No GUI.** Headless `systemd --user`
  daemon at runtime; styled TUI for install/config/diagnostics. No Rust helper (X11 makes
  injection trivial). CLI verbs: `flowlinux start|stop|status|config|doctor|model`.
  Config: TOML at `~/.config/flowlinux/config.toml`. Status cue: libnotify + optional sound.
- **Injection:** XTEST typing (xdotool) primary → clipboard-paste (xclip) → notify. Behind
  an `Injector` interface; a `WaylandInjector` slots in later.
- **Hotkey:** pynput X11 monitor, Right-Ctrl push-to-talk (M2).
- **ASR:** best-available path at startup (GPU default here, CPU universal fallback);
  faster-whisper (CT2 3.24) AND whisper.cpp-CUDA behind one interface; **M3 benchmark
  picks the default.** Model tiered by path (GPU: distil-large-v3 int8; CPU: base/small).
- **Formatting:** Tier-1 rules default; Tier-2 cloud LLM opt-in; Tier-3 local LLM off here.
- **Cloud:** opt-in, off by default.
- **UX:** terminal-first (ADR-0007) — no Qt/GUI window; install/config/diagnostics via TUI.

## Priorities (resolve tradeoffs in this order)
1. English accuracy → 2. noise robustness → 3. reliability/safety → 4. speed.

## Repo layout
```
flowlinux/
  injection/   # M1 — Injector iface, xdotool/clipboard/notify backends, manager, window, preflight
  cli.py       # M1 — `flowlinux-inject`
  core/ hotkey/ audio/ asr/ format/ tui/ diagnostics/  # stubs, filled per milestone (tui = Rich/questionary, no GUI)
bench/          # M3+ WER + latency harness
packaging/      # M7 deb/appimage/systemd
tests/          # pytest
```

## Build / run
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e .[dev]
sudo apt-get install -y xdotool xclip libnotify-bin      # system deps (X11)

pip install -e ".[hotkey,audio,asr,bench,dev]"   # M2/M3 deps (pynput, sounddevice, faster-whisper, jiwer)

echo "hello world" | flowlinux-inject            # M1: type via XTEST
echo "hello world" | flowlinux-inject --paste     # M1: clipboard paste
flowlinux record                                  # M2: hold Right-Ctrl to talk (PTT daemon)
flowlinux record --duration 2                     # M2: 2s mic test (no hotkey)
flowlinux transcribe file.wav                     # M3: transcribe a file (--inject to type it)
flowlinux dictate                                 # M3: hold Right-Ctrl -> speak -> text injected (MVP)
flowlinux doctor                                  # diagnostics: injection + audio + hotkey
pytest -q                                         # tests (ASR integration gated by env var)
FLOWLINUX_ASR_INTEGRATION=1 pytest tests/test_asr_integration.py   # silence/noise -> empty
```

## Conventions
- Python 3.10+, `from __future__ import annotations`, type hints, dataclasses.
- Backends **never raise** from `inject()` — return `InjectionResult(ok=False)` so the
  manager can escalate. Surface failures; never fail silently.
- New runtime dependency on system state ⇒ add a health check + a degraded-mode fallback.
- Keep idle footprint low: load models lazily, never hold a local LLM and Whisper at once.
- Privacy: no telemetry; audio never written to disk unless history is explicitly enabled.
- Log every notable decision in [DECISIONS.md](DECISIONS.md); track milestones in
  [ROADMAP.md](ROADMAP.md).
