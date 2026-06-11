#!/usr/bin/env bash
# FlowLinux bootstrap installer (X11). Sets up venv + deps + systemd --user service,
# then launches the TUI first-run wizard.
set -euo pipefail
cd "$(dirname "$0")"

echo "==> FlowLinux installer"

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
echo "==> Installing FlowLinux (hotkey, audio, asr, tui)"
pip install -q -U pip
pip install -q -e ".[hotkey,audio,asr,tui]"

BIN="$(pwd)/.venv/bin/flowlinux"

# 3) systemd --user service
if command -v systemctl >/dev/null 2>&1; then
  echo "==> Installing systemd --user service"
  mkdir -p "$HOME/.config/systemd/user"
  sed -e "s|@FLOWLINUX@|$BIN|g" -e "s|@DISPLAY@|${DISPLAY:-:0}|g" \
      packaging/flowlinux.service.in > "$HOME/.config/systemd/user/flowlinux.service"
  systemctl --user daemon-reload || true
  echo "   Enable autostart later with: systemctl --user enable --now flowlinux"
else
  echo "==> systemd not found; you can run the daemon with: $BIN start"
fi

# 4) first-run wizard
echo "==> Launching setup wizard"
"$BIN" setup || true
echo "==> Done. Try: $BIN dictate"
