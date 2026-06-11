#!/usr/bin/env bash
# EXPERIMENTAL AppImage build for NAVA.
#
# Embeds a *relocatable* Python (via python-appimage) plus all NAVA Python deps. The host
# still needs xdotool / xclip / x11-utils at runtime — those are separate X11 command-line
# tools NAVA shells out to and cannot be portably bundled in an AppImage.
#
# Requires:  pip install python-appimage   (downloads a manylinux Python + wheels)
set -euo pipefail
cd "$(dirname "$0")/../.."

VERSION="$(grep -m1 '^version' pyproject.toml | sed 's/.*"\(.*\)".*/\1/')"
OUT="build/appimage"
mkdir -p "${OUT}"

echo "==> Building NAVA wheel"
python3 -m pip install -q build python-appimage
python3 -m build --wheel --outdir "${OUT}/wheels"
WHEEL="$(ls "${OUT}"/wheels/nava-*.whl | head -1)"

echo "==> Preparing python-appimage recipe"
RECIPE="${OUT}/recipe"
rm -rf "${RECIPE}"; mkdir -p "${RECIPE}"
printf '%s[hotkey,audio,asr,tui]\n' "${WHEEL}" > "${RECIPE}/requirements.txt"
cp packaging/appimage/nava.desktop "${RECIPE}/nava.desktop"
# minimal placeholder icon (replace with a real PNG for a polished build)
printf 'P1\n1 1\n0\n' > "${RECIPE}/nava.png"

echo "==> Building AppImage (python-appimage, Python 3.11)"
python3 -m python_appimage build app -p 3.11 "${RECIPE}" \
        -o "${OUT}/NAVA-${VERSION}-x86_64.AppImage"
echo "==> Built ${OUT}/NAVA-${VERSION}-x86_64.AppImage"
echo "    Run:  ./${OUT}/NAVA-${VERSION}-x86_64.AppImage setup"
