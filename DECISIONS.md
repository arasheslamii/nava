# DECISIONS.md — Architecture Decision Log

Append-only, ADR-style. Newest at the bottom.

---

## ADR-0001 — Environment baseline (2026-06-10)
Dev/reference machine: Linux Mint 22 (Ubuntu 24.04), Cinnamon on **X11**, PipeWire,
i7-4720HQ (Haswell 4c/8t, AVX2), GTX 960M 4GB (Maxwell GM107, **compute capability 5.0**,
driver **470** → **CUDA 11.4** ceiling), 15 GiB RAM (swap full, ~4 GiB free idle).
**Consequence:** the usual hardest problem (Wayland injection) is absent; the binding
constraint is the ML stack (old GPU + legacy CUDA + weak CPU). Difficulty is inverted.

## ADR-0002 — X11 injection strategy (2026-06-10)
Primary = XTEST typing via `xdotool` (stdin-fed for safe Unicode). Fallbacks: clipboard
paste via `xclip` (save/set/paste/restore), then notify (clipboard + notify-send). Per-app
paste key chosen by active-window WM_CLASS (terminals → Ctrl+Shift+V, else Ctrl+V).
**Rejected for now:** the Wayland ladder (wtype/ydotool/wl-copy), uinput/evdev, input-group
setup — not needed on X11. Kept behind the `Injector` interface for a future Wayland session.

## ADR-0003 — All-Python core + PySide6 UI (2026-06-10)
Single Python stack; no Rust injection helper (X11 makes injection trivial, and Python
maximizes ML iteration speed, which dominates this project). PySide6 tray/UI speaks
StatusNotifierItem (Cinnamon supports it). **Rejected:** Rust+Tauri, Python+Rust helper.

## ADR-0004 — Cloud backends opt-in, off by default (2026-06-10)
Local/offline is the default and the privacy stance. Groq/Deepgram ASR and cloud LLM
formatting are available behind the same interfaces but disabled until the user enables
them — the realistic way to reach sub-second latency on this hardware when desired.

## ADR-0005 — ASR path + model tiering; backend chosen by benchmark (2026-06-10)
Best-available path selected at startup via health check: **GPU default on this machine**,
CPU int8 the universal fallback. Build BOTH faster-whisper (**CTranslate2 3.24.x**, CUDA 11
+ cuDNN 8) and **whisper.cpp-CUDA** (`GGML_CUDA=1`) behind one `ASRBackend`.
Model is **tiered by resolved path**, not globally fixed: GPU → distil-large-v3 / large-v3-
turbo int8; CPU → base/small int8. **Never run distil-large-v3 on the Haswell CPU** (10–20s).
**Maxwell caveat:** CC 5.0 has no dp4a/IMMA int8 acceleration and no fast FP16, so int8-on-GPU
may be slow/flaky. **M3 benchmark decides** the default backend + GPU mode (int8 vs FP32) and
**locks the winner here**. **Rejected:** Parakeet-TDT (needs CUDA 12 / modern GPU); CT2 4.x.

## ADR-0006 — Product priorities & safety (2026-06-10)
Tradeoff order: (1) English accuracy, (2) noise robustness, (3) reliability/safety, (4) speed.
Accuracy/noise are first-class: aggressive Silero VAD gating, anti-hallucination params
(beam_size≈5, condition_on_previous_text=False, no_speech/logprob thresholds, temperature
fallback), optional pre-model denoise kept only if M3 shows a WER win, and a silence→empty
golden test. Safety: offline default, no telemetry, audio off-disk unless history enabled,
health checks + degraded-mode fallbacks everywhere, crash-resilient daemon, lazy model load,
never both local-LLM and Whisper in memory (Tier-3 local LLM OFF on this box).

## M1 acceptance results (2026-06-10)
Env: Linux Mint 22, Cinnamon/X11, xdotool 3.20160805.1, xclip, xprop, libnotify.

**Automated** (driving the real `flowlinux-inject` CLI and verifying the text landed):
- GTK text-entry (zenity): type ✅, paste via **Ctrl+V** ✅
- gnome-terminal (WM_CLASS gnome-terminal-server/Gnome-terminal): type ✅, paste via
  **Ctrl+Shift+V** ✅ — per-app terminal policy confirmed live.
- Unit tests 8/8 (policy, escalation, unhealthy-skip, all-fail, Unicode clipboard round-trip).
- Live WM_CLASS detection confirmed for VS Code ("Code" → "code", treated as normal — correct,
  since VS Code maps Ctrl+V itself, including its integrated terminal).

**Two bugs found & fixed during the spike:**
1. `xclip -i` forks a background selection-owner; capturing its stdout/stderr via PIPE blocked
   until timeout, so clipboard-set always failed. Fix: redirect xclip stdout/stderr to DEVNULL.
2. `xdotool getwindowclassname` does NOT exist in xdotool 3.2016* → class always empty →
   terminals misdetected (wrong paste key). Fix: read WM_CLASS via `xprop` and match res_name
   OR res_class. Added xprop (x11-utils) to preflight.

**Manual checklist (human visual confirmation in live apps) — pending:**
Firefox text field, VS Code editor, an Electron chat app, LibreOffice Writer. Procedure:
`printf 'FlowLinux M1 ✓ café' | flowlinux-inject --wait 2` then focus the app (and the
`--paste` variant). These are the same "normal app" code path proven by zenity; any quirks
will be logged here.
