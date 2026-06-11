#!/usr/bin/env bash
# Build a .deb for NAVA. The package ships the source under /opt/nava/src and creates a
# venv in /opt/nava/venv in postinst (pip installs the Python deps from PyPI — needs network
# at install time, like most ML apps). Produces dist/nava_<version>_all.deb.
set -euo pipefail
cd "$(dirname "$0")/../.."   # repo root

VERSION="$(grep -m1 '^version' pyproject.toml | sed 's/.*"\(.*\)".*/\1/')"
PKG="nava_${VERSION}_all"
REPO="$(pwd)"
# Stage on a normal filesystem so dpkg-deb gets sane (<=0775) permissions even when the
# repo lives on a mount that forces 0777 (NTFS/exFAT/etc.).
STAGE="$(mktemp -d)"
ROOT="${STAGE}/${PKG}"
trap 'rm -rf "${STAGE}"' EXIT

echo "==> Assembling ${PKG}"
mkdir -p "${ROOT}/DEBIAN" "${ROOT}/opt/nava/src" \
         "${ROOT}/usr/lib/systemd/user" "${ROOT}/usr/share/doc/nava"
chmod 0755 "${ROOT}/DEBIAN"

# payload: the installable source (package + metadata + bundled example dictionary)
cp -r nava pyproject.toml README.md "${ROOT}/opt/nava/src/"
cp packaging/systemd/nava.service "${ROOT}/usr/lib/systemd/user/nava.service"
[ -f docs/INSTALL.md ] && cp docs/INSTALL.md "${ROOT}/usr/share/doc/nava/"

cat > "${ROOT}/DEBIAN/control" <<EOF
Package: nava
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), python3-venv, python3-pip, xdotool, xclip, x11-utils, libnotify-bin, libportaudio2
Maintainer: NAVA <nava@localhost>
Description: NAVA - local-first AI voice dictation for Linux (X11)
 Hold a hotkey, speak, and polished text is injected into the focused app.
 Local Whisper ASR (faster-whisper), Tier-1 formatting + custom dictionary,
 terminal-first UX. No telemetry; audio never written to disk.
EOF

cat > "${ROOT}/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
VENV=/opt/nava/venv
echo "Setting up NAVA Python environment (downloads dependencies from PyPI)…"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip >/dev/null
"$VENV/bin/pip" install "/opt/nava/src[hotkey,audio,asr,tui]"
ln -sf "$VENV/bin/nava" /usr/bin/nava
ln -sf "$VENV/bin/nava-inject" /usr/bin/nava-inject
echo "NAVA installed. Configure with:  nava setup"
echo "Then run in background with:      nava start   (auto-start on login: nava enable)"
EOF
chmod 0755 "${ROOT}/DEBIAN/postinst"

cat > "${ROOT}/DEBIAN/prerm" <<'EOF'
#!/bin/sh
set -e
systemctl --global disable nava.service 2>/dev/null || true
rm -f /usr/bin/nava /usr/bin/nava-inject
rm -rf /opt/nava/venv
EOF
chmod 0755 "${ROOT}/DEBIAN/prerm"

chmod -R u+rwX,go+rX "${ROOT}"
mkdir -p "${REPO}/dist"
dpkg-deb --build --root-owner-group "${ROOT}" "${REPO}/dist/${PKG}.deb"
echo "==> Built dist/${PKG}.deb"
