# Installing NAVA

NAVA is a local-first AI voice dictation app for Linux. **X11 only** for now (Wayland
support is planned behind the same injection interface).

## Requirements (all install methods)

System tools NAVA shells out to (the packages install these as dependencies):

| Tool | Debian/Ubuntu pkg | Arch pkg | Purpose |
|---|---|---|---|
| xdotool | `xdotool` | `xdotool` | XTEST typing + paste + window detection |
| xclip | `xclip` | `xclip` | clipboard backend |
| xprop | `x11-utils` | `xorg-xprop` | per-app paste policy (terminals) |
| notify-send | `libnotify-bin` | `libnotify` | optional desktop notifications |
| PortAudio | `libportaudio2` | `portaudio` | microphone capture |

Plus Python ≥ 3.10. The first install downloads the Whisper model (~250 MB for `small.en`)
on first use.

---

## Debian / Ubuntu / Linux Mint (.deb)

```bash
sudo apt install ./nava_0.0.1_all.deb     # pulls system deps; builds a venv in /opt/nava
nava setup                                 # configure (model, hotkey, cues, dictionary)
nava start                                 # run in background (systemd --user)
nava enable                                # optional: auto-start on login
```

> The `.deb` postinstall creates `/opt/nava/venv` and pip-installs NAVA's Python
> dependencies from PyPI, so the install needs network access once.

Build the .deb yourself from a checkout:

```bash
bash packaging/deb/build_deb.sh     # -> dist/nava_<version>_all.deb
```

## Arch Linux (AUR)

```bash
cd packaging/aur && makepkg -si
nava setup && nava start
```

The Python environment is created in `/opt/nava/venv` on first `nava` run.

## AppImage (experimental)

```bash
# build it (needs: pip install python-appimage):
bash packaging/appimage/build_appimage.sh
./build/appimage/NAVA-0.0.1-x86_64.AppImage setup
```

The AppImage bundles Python + all NAVA Python deps, but you must still have
`xdotool xclip x11-utils libnotify-bin` installed on the host.

## From source (developers)

```bash
git clone <repo> nava && cd nava
./install.sh        # apt deps + venv + wizard, or:
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[hotkey,audio,asr,tui,bench,dev]"
sudo apt install -y xdotool xclip x11-utils libnotify-bin libportaudio2
nava setup
```

---

## Running

```bash
nava dictate        # foreground: hold Right-Ctrl, speak, release -> text injected
nava start          # background daemon (survives closing the terminal)
nava status         # config + daemon state (+ PID)
nava stop           # stop the background daemon
nava doctor         # diagnostics (X11, xdotool, clipboard, mic, hotkey, ASR)
```

**Paste-last-transcript:** `nava paste-last` re-injects your most recent transcript — a
handy fallback. Bind it to a desktop keyboard shortcut (e.g. Cinnamon → Keyboard →
Shortcuts → Custom → command `nava paste-last`).

## Configuration

`~/.config/nava/config.toml` (hand-editable, or `nava config`). Highlights:

- `[asr] model` — `small.en` (default), `base.en` (faster), `medium.en` (more accurate, slower)
- `[hotkey] key`/`mode` — `ctrl_r` and `hold` | `toggle` | `double_tap`
- `[feedback] cues` — `off` (default, silent) | `sound-only` | `full`
- `[formatting] dictionary` — path to your custom-term corrections (`~/.config/nava/dictionary.toml`)

## Privacy

Local by default, no telemetry. Audio is never written to disk. Only the most recent
transcript is cached (for `paste-last`); disable with `[history] keep_last = false`.

## Uninstall

- .deb: `sudo apt remove nava`
- AUR: `sudo pacman -R nava`
- source: `systemctl --user disable --now nava` then delete the checkout + `~/.config/nava`
