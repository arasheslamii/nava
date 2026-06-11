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

## M2 — Hotkey + audio loop ✅
- [x] PTTController state machine: hold / toggle / double-tap (pure, unit-tested)
- [x] PynputX11Hotkey: X11 Right-Ctrl monitor, auto-repeat collapsed to single edges
- [x] AudioRecorder: sounddevice 16 kHz mono int16 (prefers pulse/pipewire); save_wav
- [x] Feedback: start/stop beeps + libnotify cues (no GUI); `--no-feedback` to silence
- [x] `flowlinux record` daemon (hold/toggle/double-tap, `--once`, `--duration` mic test)
- [x] `flowlinux doctor` extended with input-device + hotkey health
- [x] **Acceptance:** live PTT via simulated Right-Ctrl → 1.3 s hold captured to valid
      16 kHz WAV; fixed-duration mic capture verified; 20 tests pass

## M3 — Local ASR + benchmark ✅
**Step 1 — CPU baseline ✅ (proven end-to-end)**
- [x] `ASRBackend` interface + `FasterWhisperBackend` (CT2; CPU int8, small.en)
- [x] Silero VAD gating (bundled) + anti-hallucination params (beam 5,
      condition_on_previous_text=False, no_speech/logprob thresholds, temperature fallback)
- [x] `postprocess.py` hallucination filter (unit-tested) + silence/noise→empty golden (gated)
- [x] `flowlinux transcribe <file>` (+ `--inject`) and `flowlinux dictate` (hold→speak→inject MVP)
- [x] Proven: JFK clip → exact transcript (RTF 0.45 on CPU); transcribe→inject exact;
      4 s PTT hold robust; silence→empty
**Step 2 — GPU evaluation ✅ (CPU wins, locked — ADR-0009)**
- [x] CT2 3.24 + CUDA 11/cuDNN 8 via pip (`.venv-gpu`, **no sudo**); sidestepped av source-build
- [x] Benchmarked: GPU int8/fp16 unsupported on Maxwell CC 5.0; GPU float32 RTF 1.81 vs
      **CPU int8 RTF 0.45** → **default = CPU small.en int8**. whisper.cpp-CUDA not pursued
      (CUDA-11 toolkit = sudo + driver-470 incompat; CPU already wins). Abstraction kept for
      modern-GPU machines.
**Step 3 — WER benchmark + model lock ✅**
- [x] `bench/run_bench.py`: WER (jiwer, normalized) + latency p50/p95 + per-category; validated
- [x] small.en vs medium.en on personal set + LibriSpeech; **locked small.en default +
      medium.en opt-in** (ADR-0010). small.en: libri 3.2%, noisy 6%, p50 2.7s. Jargon
      proper-nouns deferred to M4 custom dictionary.

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
