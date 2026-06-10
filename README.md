# FlowLinux

System-wide, local-first AI voice dictation for Linux. Clean-room — no code, assets, or
branding from any other product.

> **Status:** early development. Milestone **M1 (text injection spike)** in progress.
> See [PLAN.md](PLAN.md), [ROADMAP.md](ROADMAP.md), [DECISIONS.md](DECISIONS.md).

## What works now (M1)

Reliable text injection into the focused window on **X11**:

```bash
echo "hello world" | flowlinux-inject          # type via XTEST (xdotool)
echo "hello world" | flowlinux-inject --paste   # clipboard set + synthesized paste
flowlinux-inject --doctor                        # diagnostics / health check
flowlinux-inject --wait 2 "focus another app"    # 2s to switch focus, then inject
```

Backends escalate automatically: **type → paste → notify** (last resort copies to
clipboard + desktop notification, so text is never lost).

## Install (dev)

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e .
sudo apt-get install -y xdotool xclip libnotify-bin   # system deps (X11)
```

## Privacy

Local by default, no telemetry, audio never written to disk unless history is explicitly
enabled. Cloud backends are opt-in and off by default.
