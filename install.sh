#!/usr/bin/env bash
# NAVA bootstrap installer (X11). Sets up venv + deps + systemd --user service,
# then launches the TUI first-run wizard.
set -euo pipefail
cd "$(dirname "$0")"

echo "==> NAVA installer"

# 1) system dependencies (X11 injection + audio)
SYS_DEPS=(xdotool xclip x11-utils libnotify-bin libportaudio2)
missing=()
for b in xdotool xclip xprop notify-send; do command -v "$b" >/dev/null 2>&1 || missing+=("$b"); done
if [ "${#missing[@]}" -gt 0 ]; then
  echo "==> Installing system deps (sudo): ${SYS_DEPS[*]}"
  sudo apt-get update -qq && sudo apt-get install -y "${SYS_DEPS[@]}"
else
  echo "==> System deps already present."
fi

# 2) Python venv + package
if [ ! -d .venv ]; then
  echo "==> Creating venv"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
. .venv/bin/activate
echo "==> Installing NAVA (hotkey, audio, asr, tui)"
pip install -q -U pip
pip install -q -e ".[hotkey,audio,asr,tui]"

BIN="$(pwd)/.venv/bin/nava"

# 3) first-run wizard (the systemd --user unit is installed on first `nava start`)
echo "==> Launching setup wizard"
"$BIN" setup || true

echo "==> Done."
echo "   • Try it now:        $BIN dictate"
echo "   • Background daemon:  $BIN start         (survives closing the terminal)"
echo "   • Auto-start on login: $BIN enable"
