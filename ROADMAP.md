# ROADMAP.md

Build vertically — each milestone is end-to-end usable. Status: ✅ done · 🔄 in progress · ⬜ todo.

## M1 — Injection spike (X11) ✅ (automated acceptance passed; manual app checklist pending)
- [x] `Injector` interface + `InjectionResult` / `HealthStatus`
- [x] `XdotoolInjector` (XTEST typing, stdin-fed for safe Unicode)
- [x] `ClipboardInjector` (xclip save → set → synthesized paste → restore)
- [x] `NotifyInjector` last-resort (clipboard + notify-send)
- [x] Active-window class detection + per-app paste policy (terminal = Ctrl+Shift+V)
- [x] `InjectionManager` escalation: type → paste → notify
- [x] CLI `flowlinux-inject` (+ `--paste`, `--wait`, `--doctor`, `--method`, `--no-restore`)
- [x] Dependency preflight + apt hint
- [x] Unit tests (policy, escalation) + clipboard round-trip
- [x] **Acceptance (automated):** gnome-terminal (type + Ctrl+Shift+V paste) and GTK entry
      (type + Ctrl+V paste) via the real CLI; results in DECISIONS.md
- [ ] **Acceptance (manual):** Firefox, VS Code, Electron chat, LibreOffice Writer visual check

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

## M5 — Tray + settings + first-run wizard ⬜
## M6 — Polish (per-app tone, paste-last-transcript, multilingual stretch) ⬜
## M7 — Packaging (.deb, AppImage, AUR, systemd user service) ⬜
