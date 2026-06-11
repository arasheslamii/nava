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

## ADR-0003 — All-Python core; no Rust helper (2026-06-10)
Single Python stack; no Rust injection helper (X11 makes injection trivial, and Python
maximizes ML iteration speed, which dominates this project). **Rejected:** Rust+Tauri,
Python+Rust helper. *(UI choice superseded by ADR-0007 — terminal-first, no Qt.)*

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

## ADR-0007 — Terminal-first UX; no GUI (supersedes the UI part of ADR-0003) (2026-06-10)
Drop PySide6/Qt entirely. Install, config, and first-run setup are a **polished terminal
UI**: `rich` for banner/colors/spinners/progress bars, `questionary` for interactive prompts
(Textual reserved for richer full-screen views if needed). An `install.sh` bootstraps the
venv + package + `systemd --user` service + autostart, then launches the TUI wizard.
**Runtime is a headless daemon** — no window. Usage = hold Right-Ctrl to talk, release to
inject (Wispr-style). Status without a window: libnotify desktop notification + optional
sound / small terminal overlay on start/stop; tray icon kept only if trivial. Config is
hand-editable TOML at `~/.config/flowlinux/config.toml` with a `flowlinux config` TUI. CLI
verbs: `flowlinux start|stop|status|config|doctor|model <download|switch>`.
**Why:** matches the desired "cool terminal setup" UX, removes GUI weight, and lowers idle
RAM (~40–90 MB vs ~80–150 with Qt) on this memory-tight machine. **Consequence:** M5 becomes
"TUI installer + config + diagnostics" instead of a Qt window; everything else (model tiering,
Whisper+VAD, noise handling, packaging) is unchanged.

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

**GUI app checklist (automated via inject → select-all → copy → read-back) — DONE:**
- **Firefox** (Gecko, URL bar): type ✅ — clipboard read-back exact.
- **VS Code** (Electron/Chromium editor): type ✅ — saved-file read-back exact incl. "café ✓".
  Covers the "Electron chat app" case (same Chromium text widget; no chat app installed).
- **LibreOffice Writer** (VCL): type delivered text but **dropped the trailing `✓` (U+2713)**;
  **paste delivered the full Unicode string intact** ✅. WM_CLASS "libreoffice-writer" → Ctrl+V.

**Finding:** XTEST typing (xdotool) drops uncommon Unicode (remapped-keycode limitation);
clipboard-paste is Unicode-safe. → see ADR-0008 (auto-routing). Accented Latin (é) typed fine
everywhere; only the symbol glyph was lost.

## ADR-0008 — Injection `auto` routing: paste for non-trivial text (2026-06-10)
M1 GUI acceptance showed XTEST typing drops uncommon Unicode (U+2713 ✓ lost in LibreOffice).
Since a dictation transcript can contain arbitrary Unicode, `InjectionManager` with `method=
"auto"` now routes to the **clipboard-paste** path (instant, Unicode-safe) when the text is
multiline, longer than 40 chars, or contains any non-ASCII char; short pure-ASCII still types
first (feels native). Escalation and the notify fallback are unchanged. `prefer_paste()` is
unit-tested. Explicit `--method type|paste` still force the order.

## M2 results (2026-06-10)
PTT hotkey + 16 kHz capture loop, end-to-end verified.
- **Hotkey:** pynput X11 listener monitors Right-Ctrl (no grab); OS auto-repeat collapsed to
  single down/up edges. State machine (`PTTController`) supports hold/toggle/double-tap, unit-
  tested with injected time. Live test: simulated `Control_R` hold (xdotool) → record → release
  → save; 1.3 s held ≈ 1.29 s captured.
- **Audio:** sounddevice InputStream, 16 kHz mono int16; input device resolves to pulse/pipewire
  (clean resample) with sounddevice-default fallback. `record_fixed()` for a headless mic test.
- **Feedback (no GUI, ADR-0007):** start/stop beeps (sounddevice sine, fade to avoid clicks) +
  libnotify; all best-effort/try-except so a cue failure never breaks capture.
- **CLI:** `flowlinux record` (`--mode`, `--key`, `--once`, `--duration`, `--no-save`,
  `--no-feedback`), `flowlinux doctor` (now incl. input-device + hotkey health), `flowlinux version`.
- **Bug caught by test:** `np.abs(int16(-32768))` overflows to -32768; peak now widens to int32.
- **Privacy note:** M2 saves WAVs for development; M3+ will gate disk writes behind history-enabled.
- 20 unit tests pass (injection 11 + hotkey 6 + audio 3).

## M3 step 1 — CPU ASR baseline (2026-06-10)
faster-whisper (CTranslate2 4.8, CPU int8, **small.en**) behind `ASRBackend`, wired into the
full pipeline: hold Right-Ctrl → record → transcribe → inject (`flowlinux dictate`).
- **Accuracy:** JFK public-domain clip → exact transcript incl. punctuation/casing.
- **Latency (Haswell CPU):** 11.0 s audio → 4.93 s infer, **RTF 0.45** (faster than real time).
  Typical ~5 s utterance ≈ ~2.5 s infer. Acceptable CPU baseline (accuracy > speed per ADR-0006).
- **VAD + anti-hallucination:** bundled Silero VAD gating; beam 5; condition_on_previous_text=
  False; no_speech/log_prob/compression thresholds; temperature fallback; plus `postprocess.py`
  segment filter. **Silence AND white-noise → empty** (gated golden tests pass).
- **End-to-end proofs (automated):** transcribe→inject exact (zenity readback); 4 s PTT hold →
  3.98 s captured (no auto-repeat early-stop); `dictate --once` runs the whole chain.
- **New CLI:** `flowlinux transcribe <file> [--inject]`, `flowlinux dictate` (MVP).
- **Note on CT2 versions:** CPU uses CT2 4.x (fine). GPU on driver-470 needs CT2 **3.24** in a
  separate env, or whisper.cpp-CUDA — M3 step 2. 29 tests (27 unit + 2 gated integration).
- **Bug fixed:** `dictate`/DictationApp didn't forward `--once` (argparse exit 2); now wired.

## ADR-0009 — Benchmark verdict: CPU is the default ASR on this machine (2026-06-10)
M3 step 2 evaluated the GPU path (GTX 960M, CT2 3.24, CUDA 11 + cuDNN 8 installed via pip
`nvidia-*-cu11` into a separate `.venv-gpu` — **no sudo**). Findings on jfk.flac (11.0 s audio):
- **GPU int8 / float16: UNSUPPORTED** — Maxwell CC 5.0 has no dp4a/IMMA int8 and no fast fp16
  (CT2: "device does not support efficient int8/float16 computation").
- **GPU float32: works, RTF 1.81** (19.9 s infer) — correct transcript but ~4× slower than CPU.
- **CPU small.en int8: RTF 0.45** (4.9 s infer), identical accuracy.

**Decision: default backend = CPU faster-whisper `small.en` int8.** The GPU is a net loss on this
card. **whisper.cpp-CUDA not pursued:** needs a CUDA-11 toolkit to compile (sudo; Ubuntu 24.04
ships CUDA 12, incompatible with driver 470), Maxwell stays fp16-limited, and CPU already wins —
avoiding the time sink (user guidance + ADR-0005). This resolves ADR-0005's "benchmark decides".
GPU eval env kept at `.venv-gpu` for reference (gitignored); the shipped app uses the CPU `.venv`
(CT2 4.x). On a *modern* GPU machine the GPU path would win — the abstraction stays in place.

## M3 step 2 — GPU evaluation (2026-06-10)
- Sidestepped a sudo wall: `av` had no cp312 wheel and tried to build from source (needs ffmpeg
  dev headers) → switched audio decoding to `soundfile` + prebuilt `av` wheel. No sudo used.
- cuDNN pitfall: `nvidia-cudnn-cu11` now resolves to **9.x**; CT2 3.24 needs **8.x** → pinned
  `nvidia-cudnn-cu11==8.9.6.50` (libcudnn.so.8). LD_LIBRARY_PATH points at the pip nvidia libs.
- Net: GPU stack *runs* (float32) but loses to CPU; see ADR-0009. ASR default stays CPU.

## M3 step 3 — WER benchmark (LibriSpeech; personal set pending) (2026-06-10)
LibriSpeech test-clean (100-utterance subset), CPU `small.en` int8:
- **WER 3.20%**, latency p50 2.83 s / p95 4.18 s, mean RTF 0.47 — strong on clean English.
- Personal 20-utterance set (plain/jargon/noisy incl. "MAAD Capital", ML terms) to be recorded
  by user; then small.en vs medium.en (accuracy + RTF) decides the locked CPU model. Harness:
  `python bench/run_bench.py --dataset {personal:<dir>|librispeech:<dir>} --configs <specs>`.

## M3 step 3 — full WER benchmark + model lock (2026-06-11)
small.en vs medium.en (CPU int8), personal 20-utterance set + LibriSpeech test-clean:

| metric                | small.en | medium.en |
|-----------------------|----------|-----------|
| LibriSpeech WER       | 3.20%    | 1.43%     |
| personal overall      | 16.67%   | 12.50%    |
| personal plain        | 13.04%   |  9.57%    |
| personal noisy        |  6.06%   |  6.06%    |
| personal jargon       | 30.12%   | 21.69%    |
| latency p50 / p95     | 2.70 / 3.55 s | 9.17 / 11.55 s |
| mean RTF              | 0.30     | 1.00 (1.84 on libri) |

Notes: personal WER is inflated by reference typos (wht, Suunday — scored vs correct ASR),
spoken-number/date formatting (forty-two thousand↔$42,000, seven↔7) and filler removal
(Whisper drops "um/like/you know" — desired, M4's job), and British↔US spelling. The genuine
gap is **proper-noun jargon** (MAAD Capital, saxa, QLoRA, LLaMA-3-8B) — **no base model gets
these; the M4 custom dictionary will**. medium ~halves clean-speech WER but costs ~3.4× latency.

## ADR-0010 — Lock CPU model: small.en default, medium.en opt-in (2026-06-11)
Default = **faster-whisper small.en int8** (responsive ~3 s/utterance, strong on plain/noisy).
**medium.en** available via `--model medium.en` for accuracy-priority use (accepts ~9 s/utt).
Already the factory default; no code change. Proper-noun jargon handled by the M4 custom
dictionary (model-independent). Re-benchmark small.en after M4 to confirm the gap closes.

## M4 step 1 — Tier-1 formatter: rules + custom dictionary (2026-06-11)
Offline, ~0 ms, default-on `FormatterPipeline` = dictionary correction → rule cleanup.
- **Custom dictionary** (`dictionary.toml`, case-insensitive, word-boundary, longest-first):
  the model-independent fix for invented proper nouns. On the personal set (small.en),
  **jargon WER 30.12% → 16.87%, overall 16.67% → 12.50%** — MAAD Capital, QLoRA, saxa,
  faster-whisper, venv, MALLOC, LLaMA-3-8B all corrected. Remaining jargon errors are
  non-dictionary (H200→HDMI left out as ambiguous, repo→ripple, a real ASR slip).
- **Rules:** conservative filler removal (um/uh/er/hmm + "you know"/"i mean"; ambiguous
  "like/actually" kept), whitespace/punctuation cleanup, sentence capitalization that does
  NOT false-split decimals (3.30), terminal-punctuation. 10 golden/unit tests.
- **Integration:** `flowlinux dictate`/`transcribe` apply Tier-1 by default (`--raw` to skip,
  `--dict <toml>` to point at a custom file; default `~/.config/flowlinux/dictionary.toml`).
  `config/dictionary.example.toml` seeded with the user's terms. Bench gained `--format/--dict`.
- **Bug fixed:** bench `by_cat` used raw hyp (hid per-category gains); now uses formatted hyp.
- Tier-2 cloud LLM (opt-in, ADR-0004) and Tier-3 local LLM (OFF here) remain for later. 37 tests.

## M5 — TUI installer + config + diagnostics (2026-06-11)
Terminal-first product layer (ADR-0007), no GUI:
- **Config:** TOML at `~/.config/flowlinux/config.toml` (`core/config.py`), nested dataclasses,
  tolerant loader (unknown keys/sections ignored, missing → defaults), tomli-w writer.
- **TUI (Rich + questionary):** ASCII banner; `flowlinux doctor` renders a Rich diagnostics
  table (session/xdotool/xclip/xprop/notify/mic/hotkey/asr) with pass/fail + readiness verdict;
  `flowlinux setup` first-run wizard (env detect → model/hotkey/mode/formatting/cues/cloud prompts
  → save config + seed dictionary → next steps); `flowlinux config` editor (same prompts, current
  values as defaults).
- **Daemon control:** `flowlinux start` = config-driven dictation daemon (foreground, what systemd
  runs); `flowlinux status` (config + service state); `flowlinux stop` (systemctl --user).
  `core/service.py` systemd --user helpers.
- **Packaging:** `install.sh` bootstrap (apt system deps → venv → `pip install -e .[...]` →
  systemd --user unit from `packaging/flowlinux.service.in` → launch wizard).
- **Validated:** Rich diagnostics render (all green here), config save/load round-trip + tolerant
  parse, start-path config→components wiring, apply_answers mapping. Wizard/config-editor are
  interactive (run `flowlinux setup`). 42 unit tests (+5 config) + 2 gated integration.

## M5 UX refinements — background daemon + quiet cues (2026-06-11)
- **Background daemon:** `flowlinux start` now installs the systemd --user unit on demand
  (ExecStart = `{python} -m flowlinux.cli_main _run`, DISPLAY/XAUTHORITY captured) and starts it
  detached, printing the PID and returning the shell; survives terminal close. `_run` is the
  internal foreground daemon with SIGTERM→clean-shutdown. Added `flowlinux enable` (auto-start
  on login). `status` shows PID; `stop` halts it. install.sh no longer hand-writes the unit.
- **Cues:** replaced per-step beeps+notifications (3 buzzes/dictation) with a single
  `feedback.cues = off | sound-only | full` toggle, **default off (silent)**. sound-only = one
  quiet start beep; full = start/stop beeps + notifications. Wired through RecorderApp/
  DictationApp + `--cues` on record/dictate + the setup/config wizard. 43 tests.

## ADR-0011 — Rename app to NAVA (2026-06-11)
Renamed the application from the working name "FlowLinux" to **NAVA**. Package `flowlinux/` →
`nava/`; console scripts `nava` + `nava-inject`; config dir `~/.config/nava/`; systemd unit
`nava.service`; env var `NAVA_ASR_INTEGRATION`; TUI banner = NAVA ASCII logo; all branding
strings updated. Historical log entries above (ADR-0001…0010, milestone results) keep their
original "flowlinux" wording as the dated record; CLAUDE.md/README rebranded. User config
auto-migrated from `~/.config/flowlinux`. 43 tests pass under the new name.

## M6 (paste-last) + M7 (packaging) (2026-06-11)
- **paste-last-transcript:** daemon persists the latest formatted transcript to
  `~/.cache/nava/last_transcript.txt` (only the last one; `[history] keep_last`, default on).
  `nava paste-last [--wait]` re-injects it from a separate process — bind to a DE shortcut for
  a hotkey. Verified live (Unicode re-injected exact). Rest of M6 deferred per user (skip cloud).
- **Packaging (M7):**
  - `.deb` (`packaging/deb/build_deb.sh`): thin package, Depends on python3/venv/pip + xdotool/
    xclip/x11-utils/libnotify-bin/libportaudio2; postinst builds `/opt/nava/venv` and pip-installs
    `nava[hotkey,audio,asr,tui]` (needs network once). Built + `dpkg-deb --info/--contents` verified.
    Staged in /tmp because the dev mount forces 0777 (dpkg-deb needs ≤0775).
  - AUR `PKGBUILD` (venv on first run), AppImage recipe + `build_appimage.sh` (python-appimage,
    experimental — host still needs xdotool/xclip), static `systemd/nava.service`.
  - Example dictionary moved into the package (`nava/data/`, package-data) so it ships in wheels/
    debs, not just the repo; wizard seeds from there. `docs/INSTALL.md` covers all paths.
