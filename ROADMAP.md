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

## M3 — Local ASR + benchmark 🔄
**Step 1 — CPU baseline ✅ (proven end-to-end)**
- [x] `ASRBackend` interface + `FasterWhisperBackend` (CT2; CPU int8, small.en)
- [x] Silero VAD gating (bundled) + anti-hallucination params (beam 5,
      condition_on_previous_text=False, no_speech/logprob thresholds, temperature fallback)
- [x] `postprocess.py` hallucination filter (unit-tested) + silence/noise→empty golden (gated)
- [x] `flowlinux transcribe <file>` (+ `--inject`) and `flowlinux dictate` (hold→speak→inject MVP)
- [x] Proven: JFK clip → exact transcript (RTF 0.45 on CPU); transcribe→inject exact;
      4 s PTT hold robust; silence→empty
**Step 2 — GPU backends ⬜ (time-boxed)**
- [ ] faster-whisper CT2 3.24 (GPU int8/fp32) on driver-470/cuDNN8 **and** whisper.cpp-CUDA,
      behind the same interface; benchmark vs CPU; fall back gracefully if CT2+cuDNN8 fights
      driver 470 (log it). **Stop for sudo CUDA-lib steps.**
**Step 3 — Benchmark harness ⬜**
- [ ] WER (jiwer) on LibriSpeech test-clean + personal set; latency p50/p95; optional denoise
      WER on/off; **lock winning backend + GPU mode in DECISIONS.md.**

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
