# Claude Code Kickoff Prompt — "FlowLinux" (working name)

Copy everything below this line into Claude Code as your first message.

---

## Mission

Build a production-quality, system-wide AI voice dictation app for Linux that matches or beats Wispr Flow in accuracy, latency, and ease of use. Wispr Flow does not exist on Linux — we are filling that gap with a clean-room implementation (no copied code, assets, or branding from Wispr).

Core user experience to replicate:
1. User holds a global hotkey (push-to-talk) or toggles hands-free mode, anywhere in the OS.
2. They speak naturally — with filler words, self-corrections, run-ons.
3. On release, polished, correctly punctuated, formatted text appears directly in whatever app/field has focus (terminal, browser, IDE, email, chat) within ~1 second.
4. An LLM post-processing layer removes fillers ("um", "like"), applies punctuation/capitalization, honors a user custom dictionary (names, jargon), and adapts tone to context.
5. A small tray icon + settings window manages everything. Zero terminal knowledge required after install.

## Phase 0 — Before writing any code (do this first)

1. Detect and report my environment: distro, desktop environment, **X11 vs Wayland** (this changes everything), audio server (PipeWire vs PulseAudio), GPU (NVIDIA/AMD/none), available RAM/VRAM.
2. Research and present a short written plan (PLAN.md) covering the architecture decisions below, with your recommendation for *my specific machine*. Wait for my approval before scaffolding.
3. Initialize the repo with: git, a CLAUDE.md (project conventions + decisions log), a DECISIONS.md (ADR-style log we append to), and a milestone roadmap.

## Architecture decisions to research and propose in PLAN.md

**A. Text injection (the hardest Linux problem — treat as Milestone 1):**
- X11: XTEST via xdotool/libxdo.
- Wayland: layered fallback strategy — `wtype` (wlr-based compositors) → `ydotool` (uinput, works everywhere but needs a daemon/udev rule the installer must set up) → clipboard-paste fallback (wl-copy + synthesized Ctrl+V, with clipboard save/restore) → "copy to clipboard + notify" as last resort.
- Must handle terminals (where Ctrl+V may not paste), IDEs, and Electron apps. Build an injection abstraction layer with per-app overrides and automatic backend selection + health check.

**B. Global hotkey:**
- X11: standard global grab.
- Wayland: evdev-based key listener (read /dev/input with proper group permissions set by installer) and/or XDG desktop portal GlobalShortcuts where supported (KDE, GNOME 45+). Support push-to-talk (hold), toggle, and double-tap modes. Default suggestion: hold Right-Ctrl or a function key; fully rebindable.

**C. ASR engine (accuracy parity):**
- Local-first: `faster-whisper` (CTranslate2) with large-v3-turbo / distil-large-v3 on GPU, small/base on CPU-only machines; evaluate NVIDIA Parakeet-TDT via onnx/NeMo as a faster alternative if I have an NVIDIA GPU.
- Optional cloud backend behind the same interface (Groq whisper-large-v3, Deepgram Nova) for users who want max speed on weak hardware — strictly opt-in, off by default (privacy is our differentiator vs Wispr).
- Streaming or chunked inference with Silero VAD so transcription starts while I'm still speaking; target ≤800 ms from key-release to text-injected for a 10-second utterance on GPU, ≤2 s on CPU with a small model.

**D. LLM formatting layer ("the Flow magic"):**
- Pluggable: local (llama.cpp / Ollama with a small instruct model, e.g. 3–8B) or API (user supplies key).
- Jobs: filler removal, punctuation, casing, paragraphing, self-correction resolution ("send it Tuesday — no wait, Wednesday" → "send it Wednesday"), custom dictionary enforcement, optional per-app tone profiles (casual in chat apps, formal in email — detect focused app via window class).
- Must be skippable (raw mode) and fast: formatting adds ≤300 ms budget. Consider running it only on utterances > N words.

**E. App shell & language:**
- Propose between: (1) Rust core + Tauri settings UI, (2) Python core (fastest ML iteration) + Rust injection helper + GTK4/Qt tray, (3) all-Python with pystray/Qt. Optimize for: low idle RAM (<300 MB without model loaded), instant mic capture start, robustness as a long-running daemon (systemd user service with autostart).
- Tray icon via StatusNotifierItem/AppIndicator. Settings UI: hotkey config, model picker with download manager + progress, dictionary editor, history of last N transcripts with "paste last transcript" action (critical fallback), audio device picker, launch-at-login toggle.

**F. Audio capture:**
- PipeWire native (with PulseAudio compat), low-latency capture at 16 kHz mono, proper device hotplug handling, input level indicator, and a visible "listening" cue (tray icon change + optional small overlay near cursor).

**G. Packaging & distribution:**
- Primary: AppImage + .deb; AUR package; evaluate Flatpak last (sandboxing fights uinput/evdev — document the tradeoff).
- Installer/first-run wizard must handle the ugly parts automatically: udev rules for uinput, adding user to `input` group, installing ydotool daemon as a user service, downloading the recommended model for detected hardware, and a built-in "test injection here" textbox + diagnostics screen.

## Milestones (build vertically — each milestone is end-to-end usable)

- **M1 — Injection spike:** prove reliable text injection into 5 target apps (gnome-terminal/konsole, Firefox, VS Code, a chat Electron app, LibreOffice) on my session type. Ship a CLI: `echo "hello" | inject`.
- **M2 — Hotkey + audio loop:** hold-to-talk records audio, beep/visual feedback, saves WAV. CLI daemon.
- **M3 — Local ASR:** wire faster-whisper + Silero VAD; key-release → raw text injected. Measure and log end-to-end latency.
- **M4 — LLM formatting:** filler removal, punctuation, custom dictionary. A/B raw vs formatted in transcript history.
- **M5 — Tray + settings UI + first-run wizard.**
- **M6 — Polish & parity:** per-app tone profiles, paste-last-transcript hotkey, multilingual support (Whisper gives this nearly free), command mode stretch goal ("new line", "delete that").
- **M7 — Packaging:** AppImage, .deb, AUR; install docs; systemd user service.

## Engineering standards

- Benchmark harness from M3 onward: WER on LibriSpeech test-clean + a personal recorded test set (have me record 20 utterances), and a latency dashboard (p50/p95 for capture→inject). Track regressions in CI.
- Every external dependency on system state (Wayland protocol, udev, ydotool) gets a runtime health check surfaced in a diagnostics panel — never fail silently.
- Unit tests for the formatting layer (golden transcript pairs), integration tests for injection where feasible.
- Log decisions in DECISIONS.md as we go. Keep CLAUDE.md updated with build/run commands and conventions.
- Privacy stance: local by default, no telemetry, audio never written to disk unless the user enables history, cloud backends clearly labeled.

## What I want from you right now (this session)

1. Run environment detection commands and show me the results.
2. Write PLAN.md with your concrete recommendations for A–G given my hardware/session, including the tradeoffs you rejected.
3. Propose the repo structure and the M1 task breakdown.
4. Ask me any blocking questions (e.g., GPU details, preferred language, whether cloud ASR is acceptable as an option).

Do not start scaffolding until I approve PLAN.md.
