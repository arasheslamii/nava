# ROADMAP.md

Build vertically — each milestone is end-to-end usable. Status: ✅ done · 🔄 in progress · ⬜ todo.

## M1 — Injection spike (X11) ✅ (acceptance passed)
- [x] `Injector` interface + `InjectionResult` / `HealthStatus`
- [x] `XdotoolInjector` (XTEST typing, stdin-fed for safe Unicode)
- [x] `ClipboardInjector` (xclip save → set → synthesized paste → restore)
- [x] `NotifyInjector` last-resort (clipboard + notify-send)
- [x] Active-window class detection + per-app paste policy (terminal = Ctrl+Shift+V)
- [x] `InjectionManager` escalation: type → paste → notify
- [x] CLI `flowlinux-inject` (+ `--paste`, `--wait`, `--doctor`, `--method`, `--no-restore`)
- [x] Dependency preflight + apt hint
- [x] Unit tests (policy, escalation) + clipboard round-trip
- [x] `auto` routing: paste for non-trivial/Unicode text, type for short ASCII (ADR-0008)
- [x] **Acceptance (automated):** gnome-terminal (type + Ctrl+Shift+V), GTK entry (type + Ctrl+V)
- [x] **Acceptance (GUI, read-back verified):** Firefox ✅, VS Code/Electron ✅, LibreOffice ✅
      (paste delivers Unicode that type drops). Results in DECISIONS.md

## M2 — Hotkey + audio loop ⬜
- pynput Right-Ctrl push-to-talk (hold/toggle/double-tap); beep + visual cue; 16kHz mono
  capture via sounddevice; save WAV; CLI daemon.

## M3 — Local ASR + benchmark ⬜
- faster-whisper (CT2 3.24) AND whisper.cpp-CUDA behind one `ASRBackend`; Silero VAD;
  anti-hallucination params; optional denoise (WER on/off). Latency dashboard (p50/p95).
  **Benchmark picks default backend + GPU mode (int8 vs FP32) → lock in DECISIONS.md.**

## M4 — Formatting ⬜
- Tier-1 rules (fillers/punct/casing/dictionary) default; optional cloud LLM; A/B raw vs
  formatted in history; golden-pair tests incl. "silence in → empty out".

## M5 — TUI installer + config + diagnostics ⬜ (no GUI)
- `install.sh` bootstrap (venv + package + systemd user service + autostart); Rich/questionary
  first-run wizard (env detect, dep install, GPU probe, model download w/ progress bar,
  diagnostics self-test + test-injection prompt); `flowlinux config` TOML editor; `flowlinux
  status`. CLI verbs: start|stop|status|config|doctor|model.
## M6 — Polish (per-app tone, paste-last-transcript, multilingual stretch) ⬜
## M7 — Packaging (.deb, AppImage, AUR, systemd user service) ⬜
