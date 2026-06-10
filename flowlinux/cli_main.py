"""`flowlinux` — top-level CLI verbs.

M2 implements: `record` (PTT capture loop / fixed-duration test), `doctor`, `version`.
Future milestones add: start|stop|status|config|model (M5).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import __version__


def _cmd_record(args) -> int:
    from .audio.capture import record_fixed, save_wav
    from .core.recorder_app import RecorderApp, default_out_dir
    from .hotkey.base import PTTMode

    # Fixed-duration mode: capture N seconds immediately, no hotkey (headless mic test).
    if args.duration is not None:
        print(f"[flowlinux] recording {args.duration}s from mic…")
        rec = record_fixed(args.duration, device=args.device)
        out_dir = Path(args.out_dir) if args.out_dir else default_out_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "fixed-capture.wav"
        save_wav(rec, str(path))
        print(f"[flowlinux] captured {rec.duration_s:.1f}s, peak {rec.peak} → {path}")
        return 0

    app = RecorderApp(
        mode=PTTMode(args.mode),
        key=args.key,
        device=args.device,
        out_dir=Path(args.out_dir) if args.out_dir else None,
        feedback_enabled=not args.no_feedback,
        save=not args.no_save,
        once=args.once,
    )
    app.run()
    return 0


def _cmd_doctor(args) -> int:  # noqa: ARG001
    from .cli import _cmd_doctor as injection_doctor

    rc = injection_doctor()
    print("\nFlowLinux audio/hotkey diagnostics")
    # audio
    try:
        import sounddevice as sd
        from .audio.capture import resolve_input_device

        dev = resolve_input_device(None)
        info = sd.query_devices(dev, "input") if dev is not None else sd.query_devices(kind="input")
        print(f"  [ok ] input device  - {info['name']} ({int(info['default_samplerate'])} Hz)")
    except Exception as e:
        print(f"  [bad] input device  - {e}")
        rc = 1
    # hotkey
    if not os.environ.get("DISPLAY"):
        print("  [bad] hotkey        - no DISPLAY (X11 required for pynput listener)")
        rc = 1
    else:
        try:
            import pynput  # noqa: F401
            print("  [ok ] hotkey        - pynput available, X11 present")
        except Exception as e:
            print(f"  [bad] hotkey        - pynput import failed: {e}")
            rc = 1
    return rc


def _cmd_version(args) -> int:  # noqa: ARG001
    print(f"flowlinux {__version__}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="flowlinux", description="FlowLinux voice dictation (terminal-first).")
    sub = p.add_subparsers(dest="cmd", required=True)

    rec = sub.add_parser("record", help="push-to-talk capture loop (or --duration for a fixed test)")
    rec.add_argument("--mode", choices=["hold", "toggle", "double_tap"], default="hold")
    rec.add_argument("--key", default="ctrl_r", help="PTT key (default ctrl_r = Right-Ctrl)")
    rec.add_argument("--device", default=None, help="input device index/name (default: pulse/pipewire)")
    rec.add_argument("--out-dir", default=None, help="where to save WAVs")
    rec.add_argument("--once", action="store_true", help="capture one utterance then exit")
    rec.add_argument("--duration", type=float, default=None,
                     help="record this many seconds immediately (no hotkey) and exit")
    rec.add_argument("--no-save", action="store_true", help="don't write WAV files")
    rec.add_argument("--no-feedback", action="store_true", help="no beeps/notifications")
    rec.set_defaults(func=_cmd_record)

    doc = sub.add_parser("doctor", help="diagnostics: injection + audio + hotkey")
    doc.set_defaults(func=_cmd_doctor)

    ver = sub.add_parser("version", help="print version")
    ver.set_defaults(func=_cmd_version)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
