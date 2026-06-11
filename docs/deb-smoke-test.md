# NAVA `.deb` smoke-test plan (clean Ubuntu/Mint VM)

Goal: verify install → daemon → dictation → **clean** uninstall on a throwaway VM, and
surface anything in the root postinstall that could fail or harm the host.

## 0. VM prep (do these first — they're the usual gotchas)

- **Snapshot the VM now** so you can revert (the postinst writes to `/opt`, `/usr/bin`, and
  pulls from PyPI — a snapshot is your clean baseline + undo).
- **Use an X11 session.** NAVA is X11-only. Default Ubuntu logs into **Wayland** → injection
  will not work. At the login screen pick **"Ubuntu on Xorg"** (gear icon), or use **Linux
  Mint Cinnamon** (X11 by default). Confirm: `echo $XDG_SESSION_TYPE` → `x11`.
- **Microphone:** most VMs have no mic. The hold-to-talk path needs a real input device —
  enable mic passthrough in the hypervisor, or use the file-based proof in §4.
- **Network:** required — the postinst downloads Python deps from PyPI, and first transcription
  downloads the Whisper model (~250 MB).
- **systemd --user:** run the daemon steps from a **graphical terminal** (not bare SSH). Over
  SSH, first run `loginctl enable-linger "$USER"` or `systemctl --user` may have no session bus.

## 1. Baseline capture (to diff against after uninstall)

```bash
ls -la /opt /usr/bin/nava* 2>/dev/null
dpkg -l | grep -i nava || echo "nava not installed (good)"
ls -la ~/.config/nava ~/.cache/nava ~/.config/systemd/user/nava.service 2>/dev/null || echo "no user state (good)"
```

## 2. Install + verify

```bash
sudo apt install ./nava_0.0.1_all.deb        # resolves system deps; runs postinst
echo "apt exit: $?"                            # MUST be 0
dpkg -l nava                                   # state should be 'ii'
dpkg -L nava                                   # files dpkg tracks (note: NOT /usr/bin/nava — see audit)
test -x /opt/nava/venv/bin/nava && echo "venv ok"
command -v nava && nava version                # -> nava 0.0.1
nava doctor                                    # expect all required checks green on X11
```

Expected: apt exit 0; `nava doctor` shows session X11 ✓, xdotool/xclip/xprop/notify ✓, mic ✓
(if a mic exists), hotkey ✓, asr ✓.

## 3. Daemon lifecycle + persistence

```bash
nava setup                 # pick small.en / Right-Ctrl / cues off; seeds ~/.config/nava/dictionary.toml
nava start                 # -> "running in background (PID …)"; prompt returns immediately
nava status                # daemon: running in background (PID …)
systemctl --user status nava.service --no-pager
# survives terminal close:
exit            # close the terminal, open a new one
nava status                # still running
# autostart across reboot:
nava enable                # systemctl --user enable --now
sudo reboot
# after logging back into the X11 session:
nava status                # running again
nava stop                  # stops cleanly
```

## 4. Dictation functional test

**With a working mic (real hardware / passthrough):**
```bash
nava dictate               # hold Right-Ctrl, say a sentence, release -> text injects into focus
```
Open a text editor, focus it, hold Right-Ctrl, speak, release → polished text appears.

**Without a mic (VM) — prove transcribe → format → inject end-to-end:**
```bash
curl -fsSL -o /tmp/jfk.flac https://raw.githubusercontent.com/openai/whisper/main/tests/jfk.flac
gedit &                                        # focus this window within 2s
( sleep 2; nava transcribe /tmp/jfk.flac --inject ) &
# -> "And so, my fellow Americans, ask not what your country can do for you…" appears in gedit
nava paste-last                                # re-injects the same transcript (fallback path)
```

## 5. Uninstall + leftover audit  ⚠️ (this is where "nothing behind" usually fails)

```bash
nava stop 2>/dev/null                          # stop the per-user daemon FIRST (see audit #5/#6)
systemctl --user disable --now nava.service 2>/dev/null
sudo apt remove nava                           # runs prerm; removes dpkg-tracked files + venv
# verify package-side removal:
dpkg -l | grep -i nava || echo "package removed"
ls /opt/nava/venv /usr/bin/nava 2>/dev/null && echo "LEFTOVER!" || echo "binaries gone"

# now hunt for what apt remove does NOT clean:
pgrep -af "nava .*_run|nava/cli_main" && echo "DAEMON STILL RUNNING!" || echo "no daemon process"
ls -d /opt/nava 2>/dev/null                                   # possibly empty dir left
ls ~/.config/nava ~/.cache/nava 2>/dev/null                   # user config + last transcript (left)
ls ~/.config/systemd/user/nava.service 2>/dev/null            # unit written by `nava start` (left)
du -sh ~/.cache/huggingface 2>/dev/null                       # Whisper model ~250MB (left)

# full manual cleanup for a truly clean machine:
sudo apt purge nava
sudo rm -rf /opt/nava
rm -rf ~/.config/nava ~/.cache/nava ~/.config/huggingface ~/.cache/huggingface
rm -f ~/.config/systemd/user/nava.service && systemctl --user daemon-reload
```

## 6. Acceptance checklist

- [ ] `apt install` exits 0; `dpkg -l nava` = `ii`
- [ ] `nava version` / `nava doctor` work; doctor all-green on X11
- [ ] `nava start` returns the shell; daemon runs detached, survives terminal close + reboot
- [ ] dictation injects text (mic) OR `nava transcribe --inject` + `nava paste-last` work
- [ ] `apt remove` exits 0; `/opt/nava/venv` and `/usr/bin/nava*` gone; no broken dpkg state
- [ ] after documented cleanup: no running process, no `/opt/nava`, no `~/.config|.cache/nava`

---

## Appendix — postinst/prerm risk audit

The package runs this **as root** at install:

```sh
set -e
python3 -m venv /opt/nava/venv
/opt/nava/venv/bin/pip install --upgrade pip
/opt/nava/venv/bin/pip install "/opt/nava/src[hotkey,audio,asr,tui]"
ln -sf /opt/nava/venv/bin/nava /usr/bin/nava
ln -sf /opt/nava/venv/bin/nava-inject /usr/bin/nava-inject
```

### Will-fail / can-break-the-system

1. **Network pip under `set -e` breaks dpkg.** If PyPI is unreachable or any dependency fails
   to install/build, postinst exits non-zero → the package is left **half-configured**, and
   apt is wedged until the user fixes it. *Recommended fix:* build the venv lazily on first run
   (as the AUR launcher does) so postinst can't fail dpkg; or make the pip step non-fatal and
   surface a clear "run `nava setup` to finish" message.
2. **Unmanaged files.** `/usr/bin/nava*` and `/opt/nava/venv` are created by the script, **not**
   tracked by dpkg (`dpkg -L nava` won't list them). Their lifecycle depends entirely on prerm;
   if prerm is skipped they orphan. Prefer dpkg-shipped wrapper(s) in `/usr/bin`.
3. **`Architecture: all` is wrong.** The venv pulls arch-specific binary wheels (ctranslate2,
   onnxruntime, numpy). On arm64/i386 the wheels may be missing → source build → failure (#1).
   Set `Architecture: amd64` and document x86_64-only (or build per-arch).

### Security / hygiene

4. **pip-as-root from PyPI.** Installs run arbitrary package build hooks **as root**, and deps
   are loosely pinned (`faster-whisper>=1.0`, …) → non-reproducible and a supply-chain surface
   at install time. *Fix:* pin a lockfile; install as a dedicated unprivileged user; or ship
   vendored wheels and `pip install --no-index`.
5. **Uninstall is not clean.** `apt remove` leaves: a **running per-user daemon**, the
   `nava start`-written `~/.config/systemd/user/nava.service`, `~/.config/nava`, `~/.cache/nava`,
   the `~/.cache/huggingface` model, and possibly an empty `/opt/nava`. The brief's "nothing
   behind" needs the §5 manual cleanup or script hardening.
6. **`systemctl --global disable` in prerm is the wrong tool.** Users enable with
   `systemctl --user enable` (`nava enable`); `--global disable` won't match it, won't stop a
   running per-user instance, and **runs on upgrade too** (rebuilds the venv every upgrade). A
   root maintainer script fundamentally cannot stop another user's `--user` daemon — document
   "run `nava stop` before removal", or ship a `postrm` note.

### Minor

7. `rm -rf /opt/nava/venv` as root — path is constant so it's safe, but flagged by lintian-style
   review; guard with a literal-path check if kept.
8. No `postrm purge` cleanup; `apt purge` won't remove `/opt/nava` or user state.
9. Hundreds of MB in `/opt/nava/venv` + ~250 MB model in `~/.cache/huggingface` — disk note.

> Net: the `.deb` is fine for a controlled/personal install, but before publishing widely I'd
> (a) move venv creation to first-run so postinst can't break dpkg, (b) set `Architecture: amd64`,
> (c) pin deps, and (d) add `nava stop` to the remove path + document the user-state cleanup.
