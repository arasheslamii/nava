# NAVA

Local-first AI voice dictation for Linux (**X11**). Hold a key, speak, and polished text is
injected into whatever app has focus. Clean-room — no code, assets, or branding from any
other product.

> **Status:** M1–M7 complete. Local Whisper ASR, Tier-1 formatting + custom dictionary,
> terminal-first TUI, background `systemd --user` daemon, and `.deb` / AUR / AppImage packaging.

## Quickstart (Debian / Ubuntu / Mint)

```bash
sudo apt install ./nava_0.0.1_all.deb     # installs system deps + a venv in /opt/nava
nava setup                                 # pick model / hotkey / cues; seeds your dictionary
nava start                                 # background daemon: hold Right-Ctrl, speak, release
nava enable                                # optional: auto-start on login
```

Other distros / from source / AppImage: see **[docs/INSTALL.md](docs/INSTALL.md)**.

## Commands

| Command | What it does |
|---|---|
| `nava dictate` | foreground: hold Right-Ctrl → speak → release → inject |
| `nava start` / `stop` / `status` | background daemon (systemd --user) |
| `nava enable` | auto-start on login |
| `nava paste-last` | re-inject the most recent transcript (bind to a DE shortcut) |
| `nava setup` / `config` | TUI wizard / config editor |
| `nava doctor` | diagnostics (X11, xdotool, clipboard, mic, hotkey, ASR) |
| `echo hi \| nava-inject` | low-level text injection |

## How it works

- **Injection (X11):** XTEST typing → clipboard-paste → notify, with automatic per-app paste
  policy and Unicode-safe routing.
- **ASR:** faster-whisper `small.en` int8 on CPU (~0.45 RTF on a 2015 i7), Silero VAD +
  anti-hallucination params (silence → empty). `medium.en` available for more accuracy.
- **Formatting:** filler removal + custom-dictionary proper-noun correction (Tier-1, ~0 ms).
- **UX:** terminal-first (Rich + questionary), headless daemon, no GUI.

## Privacy

Local by default, no telemetry, audio never written to disk. Only the latest transcript is
cached (for `paste-last`); disable with `[history] keep_last = false`.

See [PLAN.md](PLAN.md), [ROADMAP.md](ROADMAP.md), [DECISIONS.md](DECISIONS.md).
