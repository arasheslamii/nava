# PLAN.md — Linux Voice Dictation (working name: "FlowLinux")

> Status: **DRAFT for approval.** No scaffolding until this is approved.
> Date: 2026-06-10. Target machine: see "Detected environment" below.

---

## 0. Detected environment (this machine)

| Area | Value |
|---|---|
| Distro | Linux Mint 22 "Wilma" (Ubuntu 24.04 base), kernel 6.8.0-90 |
| Desktop / session | Cinnamon, **X11** (`XDG_SESSION_TYPE=x11`) |
| Audio | PipeWire 1.0.5 + WirePlumber, PulseAudio compat shim |
| CPU | Intel i7-4720HQ — Haswell, 4 cores / 8 threads, AVX2 (no AVX-512) |
| GPU | NVIDIA GTX 960M (Maxwell GM107), 4 GB VRAM (~3 GB free), compute capability 5.0 |
| GPU driver | 470.256.02 → **CUDA 11.4 max**; CUDA toolkit (nvcc) not installed |
| RAM | 15 GiB total (~4 GiB free at probe time, swap full) |
| Injection tools present | `xclip` only. Missing: xdotool, wtype, ydotool, wl-copy/paste |
| Dev toolchain | python 3.12, pip 25, cargo/rustc 1.85, node 20, gcc 13, git 2.43 |
| Group membership | `arash adm cdrom sudo dip plugdev users lpadmin sambashare docker kvm` — **not in `input`** |
| /dev/uinput | present, `root:root` `crw-rw----` (no user access yet) |

### What this environment changes vs the generic plan
1. **Session is X11, not Wayland.** The single hardest item in the brief (Milestone-1 Wayland injection) collapses to a well-trodden path: XTEST via xdotool. The whole `wtype → ydotool → wl-copy` fallback ladder, udev rules, `input`-group setup, and ydotool daemon are **not required for this machine**. We still build the injection *abstraction* so a future Wayland session is supported, but it is not on the critical path now.
2. **The ML stack is the real constraint, and it is inverted in difficulty.** GTX 960M (Maxwell, CC 5.0, 4 GB) on **driver 470 / CUDA 11.4** cannot run the modern, fast paths the brief assumes:
   - CTranslate2 4.x (current faster-whisper backend) needs CUDA 12 + cuDNN 9 → **incompatible**. We must pin **CTranslate2 3.24.x** (CUDA 11 + cuDNN 8) for any GPU use.
   - NVIDIA Parakeet-TDT (NeMo/onnx) effectively needs a modern GPU + CUDA 12 → **rejected for this machine.**
   - Maxwell has no fast FP16 → GPU inference must use **int8**, not float16.
3. **The brief's latency targets are not reachable locally on this hardware.** Honest estimates below. Cloud (opt-in) or relaxed targets are the realistic options. This is the most important decision to make up front (see §8 Questions).

---

## Product priorities (rank tradeoffs in this order)

1. **English accuracy** — get the words right.
2. **Robust background-noise handling** — VAD-gated, denoise option, anti-hallucination params.
3. **Reliability / safety** — never fail silently, degraded-mode fallbacks, crash-resilient daemon, offline by default.
4. **Speed** — as fast as the hardware allows, *after* the above.

> Genuinely accurate and dependable first; fast second. When two goals conflict, the lower number wins.

### Safety / reliability requirements
- **Offline by default**, no telemetry, audio never written to disk unless history is explicitly enabled.
- **Never fail silently:** runtime health checks for X11, xdotool, clipboard, GPU/CUDA stack, mic — surfaced in diagnostics — each with a clean **degraded-mode fallback** (GPU fails → CPU; inject fails → clipboard + notify).
- **Crash-resilient daemon:** the capture→ASR→inject loop is wrapped so one bad utterance cannot kill the long-running `systemd --user` process; log and recover.
- **Memory discipline (this box: swap full, ~4 GiB free idle):** load model lazily, unload when idle if needed, and **never hold a local LLM and Whisper in memory at once.** Tier-3 local LLM stays **OFF** on this machine.

---

## A. Text injection — **LOW RISK here (X11)**

**Recommendation:** abstraction layer `Injector` with backend auto-selection + health check. For this X11 machine:

- **Primary backend — XTEST typing via `xdotool type --clearmodifiers`.** Robust Unicode, works in browsers, IDEs, GTK/Qt apps. (Requires `apt install xdotool`.)
- **Paste fallback — clipboard via `xclip` (already installed).** For long text, heavy Unicode/emoji, or apps where synthetic typing is slow/unreliable. Save → set clipboard → synthesize paste → restore clipboard.
- **Per-app overrides keyed on window class** (`xdotool getactivewindow getwindowclassname`):
  - Terminals (gnome-terminal, konsole, xterm, alacritty, kitty): paste = **Ctrl+Shift+V**, or primary-selection middle-click.
  - Everything else: **Ctrl+V**.
- **Last-resort:** "copied to clipboard + notify" (libnotify) if focus/inject fails.
- **Health check** at startup and in diagnostics: confirm X11, `xdotool` present, can query active window, can read/write clipboard.

**Rejected for now:** the Wayland ladder (wtype/ydotool/wl-copy), uinput injection. Kept behind the interface as a future `WaylandInjector`, not built in M1.

**M1 still earns its keep:** even though injection is easy on X11, the per-app terminal/Electron edge cases are real, so M1 = prove 5 apps end-to-end and ship `echo "hello" | flowlinux-inject`.

---

## B. Global hotkey — **LOW RISK here (X11)**

**Recommendation:** X11 key monitoring via **`pynput`** (or python-xlib) — no grab needed for push-to-talk since we only *observe* the modifier, we don't consume it.

- Default PTT = **hold Right-Ctrl** (rebindable). Modes: hold (PTT), toggle, double-tap.
- No `input` group / evdev needed on X11 → avoids the permissions mess entirely.
- Keep an optional **evdev backend** (`/dev/input`, session-agnostic) behind the same interface for future Wayland; it would require the installer to add the user to `input` — documented but **not used by default**.
- XDG GlobalShortcuts portal is **not available** under Cinnamon (only gtk/gnome-keyring/xapp portals present) → not an option here; the X11 monitor is the path.

---

## C. ASR engine — **the fragile part on this machine**

### Honest latency estimates (10 s utterance, key-release → text)
| Path | Model | Precision | Est. latency | Notes |
|---|---|---|---|---|
| GPU (960M, CT2 3.24) | distil-large-v3 / large-v3-turbo | int8 | **~1.5–3 s** | needs cuDNN8/CUDA11 runtime; VRAM-tight |
| GPU (960M, whisper.cpp CUDA) | small / medium | q5 | **~1.5–3 s** | more forgiving of old CUDA/Maxwell |
| CPU (Haswell, CT2) | small | int8 | **~4–8 s** | misses target badly |
| CPU (Haswell, CT2) | base | int8 | **~2–4 s** | usable, lower accuracy |
| **Cloud (Groq whisper-large-v3-turbo)** | — | — | **~0.3–0.8 s** | opt-in; best UX; privacy tradeoff |

> ⚠️ The brief's **≤800 ms GPU** target is **not achievable on a GTX 960M**. Realistic local floor is ~1.5 s. Only the cloud path hits sub-second.

### Recommendation (LOCKED: best-available path, model tiered by path, English-only)
- **Startup path selection via health check.** Probe for a usable CUDA stack; **GPU is the default on this machine**, CPU is the universal fallback. The model is chosen from the *resolved* path — never a global fixed model:
  - **GPU path →** distil-large-v3 (or large-v3-turbo) **int8** (~1.5 GB).
  - **CPU fallback →** base/small int8. **Never distil-large-v3 on CPU** (unusably slow on Haswell).
- **Two GPU backends, benchmark decides.** Build `faster-whisper` (CT2 **3.24.x**) AND `whisper.cpp`-CUDA (`GGML_CUDA=1`) behind one `ASRBackend`. M3 benchmarks them (int8 **and** FP32 modes) on this card and **locks the winner in DECISIONS.md.** Maxwell CC 5.0 has no dp4a/IMMA int8 and no fast FP16, so don't assume int8 wins — whisper.cpp-CUDA and/or FP32 may be more stable.

### Accuracy & noise-robustness (priority #1 and #2 — first-class)
- **Silero VAD aggressively** gates non-speech and trims silence — this is our primary noise defense (don't transcribe what isn't speech) and it cuts perceived latency.
- **Accuracy/anti-hallucination params** (config-surfaced, sane defaults): `beam_size≈5`, `condition_on_previous_text=False` (stops noise-induced repetition loops), `no_speech_threshold` + `log_prob_threshold` to drop garbage segments, temperature fallback enabled.
- **Optional pre-model denoise** (RNNoise / noisereduce), toggleable. M3 benchmarks WER with it on vs off; **keep on only if it measurably helps.**
- **Whisper silence-hallucination guard:** VAD gate + no_speech threshold + drop empty/low-confidence segments. **Golden test:** silence/noise in → empty out, never invented text.
- **Robustness backend:** `whisper.cpp` compiled with CUDA (`GGML_CUDA=1`) as an alternative GPU path — it tolerates Maxwell/CUDA-11 better than CT2. Both sit behind one `ASRBackend` interface; we benchmark both in M3 and keep the winner as default.
- **VAD:** Silero VAD for chunked/streaming inference so transcription overlaps speech and trims silence (cuts perceived latency).
- **VRAM budget:** ~3 GB free. distil-large-v3 int8 ≈ 1.5 GB → fits. Do **not** also hold an LLM on the GPU at the same time (see D).
- **Cloud backend (opt-in, off by default):** Groq / Deepgram behind the same interface, clearly labeled — the realistic way to get Wispr-class latency on this hardware.

**Rejected:** Parakeet-TDT (needs modern GPU/CUDA 12), CT2 4.x + float16 (incompatible driver, no fast FP16).

---

## D. LLM formatting layer ("the Flow magic")

**Reality:** a local 3–8B model cannot hit the ≤300 ms budget on this CPU, and sharing the 4 GB GPU with Whisper is not feasible. So formatting is **tiered and pluggable**, with a strong no-model default:

- **Tier 1 — Rule-based (DEFAULT, ~0 ms, offline):** filler-word removal (configurable list: "um, uh, like, you know…"), capitalization, sentence punctuation heuristics, spacing, and **custom-dictionary substitution** (names/jargon). Deterministic, unit-testable with golden pairs. Delivers ~80% of the perceived polish for free on weak hardware.
- **Tier 2 — Cloud LLM (opt-in, recommended for full magic):** self-correction resolution ("send it Tuesday — no, Wednesday" → "Wednesday"), paragraphing, per-app tone. Recommended model: **Claude Haiku 4.5** (`claude-haiku-4-5`) for low-latency/low-cost, or Groq Llama for ultra-cheap. ~300–700 ms, user supplies key.
- **Tier 3 — Local LLM (opt-in, offline):** llama.cpp with a small instruct model (e.g. Qwen2.5-3B-Instruct int4) on CPU for users who want offline magic and accept ~1–3 s. GPU offload only when Whisper is unloaded.

All tiers are **skippable (raw mode)** and gated by utterance length (skip LLM for < N words). Per-app tone profiles keyed on window class.

---

## E. App shell & language

**Recommendation: all-Python core + Qt (PySide6) UI.**
- **Why Python core:** the entire ML stack (faster-whisper, Silero, llama.cpp bindings, sounddevice) is Python-first → fastest iteration, which matters most given the hardware tuning ahead. On X11 there is **no need for a Rust injection helper** (xdotool/pynput cover it), which removes the main reason to go polyglot.
- **UI/tray:** PySide6 — `QSystemTrayIcon` speaks StatusNotifierItem, which Cinnamon's native systray supports. Settings window in the same toolkit.
- **Daemon:** long-running `systemd --user` service + XDG autostart entry. Idle RAM (Python + Qt, model unloaded) ≈ 80–150 MB — within the <300 MB goal.
- **Rejected:** Rust-core + Tauri (slows ML iteration, buys little when injection is trivial on X11); Python + Rust helper (unnecessary complexity here).

> This is a genuine fork — see Question 1. If you prefer Rust/Tauri for the shell, the plan adapts (Python ML sidecar + Tauri UI).

---

## F. Audio capture

**Recommendation:** `sounddevice` (PortAudio) capturing **16 kHz mono** through PipeWire-Pulse.
- Input level indicator via RMS; "listening" cue = tray icon state change + optional small Qt overlay near cursor.
- Device hotplug: subscribe to PipeWire/Pulse events (or periodic re-enumerate); device picker in settings.
- Audio **never written to disk** unless history is explicitly enabled.

---

## G. Packaging & distribution

Ordered for *this* machine's ecosystem (Mint/Ubuntu):
1. **`.deb`** (primary) — apt deps: `xdotool`, `xclip`, `libportaudio2`, optionally CUDA-11 cuDNN8 runtime for GPU.
2. **AppImage** (portable) — bundle Python via python-appimage.
3. **AUR** + **Flatpak** later. Flatpak note: sandbox fights uinput/evdev *and* X11 synthetic input — documented tradeoff; not first.

**First-run wizard handles the ugly parts:**
- Detect X11 (✓ here) → skip the whole Wayland/uinput/input-group setup.
- `apt install xdotool` if missing; verify xclip.
- GPU probe: detect driver 470/CUDA 11.4 → offer GPU (CT2 3.24 + cuDNN8) or CPU path; download the recommended model for the chosen path with progress.
- Built-in **"test injection here" textbox** + **diagnostics panel** (X11 ✓, xdotool ✓, clipboard ✓, GPU/CUDA, mic capture, latency self-test).

---

## Recommended repo structure (proposal — not yet created)

```
flowlinux/
├─ CLAUDE.md                 # conventions + decisions log + build/run commands
├─ DECISIONS.md              # ADR-style append-only log
├─ PLAN.md                   # this file
├─ ROADMAP.md                # milestone tracker
├─ pyproject.toml            # deps, entry points (flowlinuxd, flowlinux-inject)
├─ flowlinux/
│  ├─ core/                  # daemon, state machine, config
│  ├─ injection/             # Injector iface; XdotoolInjector, ClipboardInjector, (WaylandInjector stub)
│  ├─ hotkey/                # Hotkey iface; PynputX11Hotkey, (EvdevHotkey stub)
│  ├─ audio/                 # capture (sounddevice), VAD (Silero), level meter
│  ├─ asr/                   # ASRBackend iface; FasterWhisper(CT2 3.24), WhisperCpp, Groq, Deepgram
│  ├─ format/               # FormatterTier1(rules), FormatterCloud, FormatterLocalLLM; dictionary
│  ├─ ui/                    # PySide6 tray + settings + first-run wizard + diagnostics
│  └─ diagnostics/           # health checks surfaced in UI
├─ bench/                    # WER + latency harness (LibriSpeech + personal set)
├─ packaging/                # deb/, appimage/, systemd user unit, autostart
└─ tests/                    # formatter golden pairs, injection integration
```

---

## M1 task breakdown — Injection spike (X11)

1. Repo init: git, `pyproject.toml`, CLAUDE.md, DECISIONS.md, ROADMAP.md, venv.
2. `Injector` interface + `XdotoolInjector` (XTEST type) + `ClipboardInjector` (xclip save/set/paste/restore).
3. Active-window class detection + per-app paste-key policy (terminal vs normal).
4. Backend auto-select + health check; libnotify last-resort.
5. CLI: `echo "hello world" | flowlinux-inject` (and a `--paste` mode).
6. **Acceptance:** reliable injection into **gnome-terminal/your terminal, Firefox, VS Code, an Electron chat app, LibreOffice Writer** on this X11 session. Document any per-app quirks in DECISIONS.md.
7. Installer preflight: detect missing `xdotool`, prompt to `apt install`.

---

## Milestones (unchanged structure, re-scoped for X11 + weak GPU)

- **M1** Injection spike (above). *Low risk here.*
- **M2** Hotkey (pynput, Right-Ctrl PTT) + audio loop (sounddevice 16 kHz) + visual/beep cue → save WAV.
- **M3** Local ASR: faster-whisper (CT2 3.24, GPU int8) **and** whisper.cpp-CUDA behind one interface + Silero VAD; key-release → raw text injected; **latency dashboard** (p50/p95). Pick default backend by benchmark.
- **M4** Formatting: Tier-1 rules (fillers/punct/dictionary) default + optional cloud LLM; A/B raw vs formatted in history; golden-pair unit tests.
- **M5** Tray + settings UI + first-run wizard + diagnostics.
- **M6** Polish: per-app tone, paste-last-transcript hotkey, multilingual (if chosen), command-mode stretch.
- **M7** Packaging: .deb + AppImage + systemd user service + docs.

---

## Locked decisions (resolved 2026-06-10)
1. **Shell/language:** ✅ **All-Python + PySide6.** Single stack, portable, production-ready on any Linux machine; no Rust helper needed on X11.
2. **Cloud backends:** ✅ **Opt-in, off by default.** Fully offline out of the box; Groq/Deepgram ASR + cloud LLM formatter available when the user enables them.
3. **Local ASR compute:** ✅ **Best-available-path selection at startup (health-check driven), GPU default on this machine.** Build BOTH `faster-whisper` (CT2 3.24) and `whisper.cpp`-CUDA behind one `ASRBackend`; **the M3 benchmark picks the default and locks it in DECISIONS.md.** CPU int8 is the universal fallback when the GPU health check fails. GPU libs optional via first-run wizard.
   - ⚠️ **Maxwell hardware fact:** GTX 960M is GM107, **compute capability 5.0** — **no dp4a/IMMA int8 acceleration** (Pascal CC 6.1+ only) and **no fast FP16**. So CT2 int8-on-GPU may NOT be ~2x and may be flaky/slow. Benchmark int8 **and FP32** GPU modes; FP32 may be the most stable even if slower. Expect whisper.cpp-CUDA may win — let data decide.
4. **Languages / model:** ✅ **English-only**, but **model is tiered by the resolved compute path, not globally fixed:** GPU path → distil-large-v3 (or large-v3-turbo) int8; CPU fallback path → base/small int8. **Never run distil-large-v3 on the Haswell CPU** (10–20 s/utterance — unusable). Model is chosen from the resolved path at startup.

---

## Engineering standards (carried from brief)
- Benchmark harness from M3: WER on LibriSpeech test-clean + a 20-utterance personal set; latency p50/p95 capture→inject; track regressions.
- Every system dependency (X11, xdotool, clipboard, GPU/CUDA, mic) gets a runtime health check surfaced in diagnostics — never fail silently.
- Unit tests for formatter (golden pairs); injection integration tests where feasible.
- DECISIONS.md updated as we go; CLAUDE.md holds build/run + conventions.
- Privacy: local by default, no telemetry, audio never persisted unless history enabled, cloud backends clearly labeled and off by default.
