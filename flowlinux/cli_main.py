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


def _cmd_transcribe(args) -> int:
    from .asr.factory import build_backend
    from .audio.load import load_audio_file

    backend = build_backend(engine=args.engine, model=args.model, device=args.device,
                            compute_type=args.compute_type, vad=not args.no_vad)
    audio = load_audio_file(args.path)
    result = backend.transcribe(audio, 16_000)
    text = result.text
    if text and not args.raw:
        from .format.pipeline import build_pipeline
        fr = build_pipeline(dict_path=args.dict).format(text)
        if fr.changed:
            print(f"[fmt] {', '.join(fr.notes) or 'cleaned'}", file=sys.stderr)
        text = fr.text
    print(text)
    print(f"[asr] {backend.name} | {result.duration_s:.1f}s audio | {result.infer_s:.2f}s "
          f"infer (rtf {result.rtf:.2f}) | dropped {result.dropped}", file=sys.stderr)
    if args.inject and text:
        from .injection.manager import InjectionManager
        res = InjectionManager().inject(text, method=args.method)
        print(f"[inject] {'ok' if res.ok else 'FAILED'} via {res.backend}: {res.detail}",
              file=sys.stderr)
        return 0 if res.ok else 1
    return 0


def _cmd_dictate(args) -> int:
    from .asr.factory import build_backend
    from .core.dictation import DictationApp
    from .hotkey.base import PTTMode

    backend = build_backend(engine=args.engine, model=args.model, device=args.device,
                            compute_type=args.compute_type, vad=not args.no_vad)
    from .format.pipeline import build_pipeline
    formatter = build_pipeline(dict_path=args.dict, enabled=not args.raw)
    app = DictationApp(
        backend=backend, mode=PTTMode(args.mode), key=args.key, device=args.audio_device,
        inject=not args.no_inject, method=args.method,
        feedback_enabled=not args.no_feedback, save_audio=args.save_audio, once=args.once,
        formatter=formatter,
    )
    app.run()
    return 0


def _cmd_doctor(args) -> int:  # noqa: ARG001
    from .tui.diagnostics import render_diagnostics

    return 0 if render_diagnostics() else 1


def _cmd_setup(args) -> int:  # noqa: ARG001
    from .tui.wizard import run_setup

    return run_setup()


def _cmd_config(args) -> int:  # noqa: ARG001
    from .tui.wizard import run_config_editor

    return run_config_editor()


def _cmd_status(args) -> int:  # noqa: ARG001
    from .core.config import Config, default_config_path
    from .core.service import status_text

    cfg_path = default_config_path()
    print(f"FlowLinux status")
    print(f"  config  : {'present' if cfg_path.exists() else 'missing (run flowlinux setup)'} "
          f"({cfg_path})")
    if cfg_path.exists():
        c = Config.load()
        print(f"  model   : {c.asr.model} ({c.asr.device}/{c.asr.compute_type})")
        print(f"  hotkey  : {c.hotkey.key} [{c.hotkey.mode}]   formatting: "
              f"{'on' if c.formatting.enabled else 'off'}   cloud: "
              f"{'on' if c.cloud.enabled else 'off'}")
    print(f"  daemon  : {status_text()}")
    return 0


def _cmd_start(args) -> int:  # noqa: ARG001
    from .asr.factory import build_backend
    from .core.config import Config
    from .core.dictation import DictationApp
    from .format.pipeline import build_pipeline
    from .hotkey.base import PTTMode

    c = Config.load()
    backend = build_backend(model=c.asr.model, device=c.asr.device,
                            compute_type=c.asr.compute_type, vad=c.asr.vad)
    formatter = build_pipeline(dict_path=c.formatting.dictionary, enabled=c.formatting.enabled)
    app = DictationApp(
        backend=backend, mode=PTTMode(c.hotkey.mode), key=c.hotkey.key,
        device=(c.audio.device or None), method=c.injection.method,
        feedback_enabled=(c.feedback.sound or c.feedback.notify), formatter=formatter,
    )
    app.run()
    return 0


def _cmd_stop(args) -> int:  # noqa: ARG001
    from .core.service import stop

    ok, msg = stop()
    print(f"flowlinux: {msg}")
    return 0 if ok else 1


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

    tr = sub.add_parser("transcribe", help="transcribe an audio file (optionally inject)")
    tr.add_argument("path", help="audio file (wav/flac/mp3/...)")
    tr.add_argument("--engine", default="faster-whisper")
    tr.add_argument("--model", default=None, help="model size (default small.en on CPU)")
    tr.add_argument("--device", default="cpu", choices=["cpu", "cuda", "auto"])
    tr.add_argument("--compute-type", default="int8")
    tr.add_argument("--no-vad", action="store_true", help="disable Silero VAD gating")
    tr.add_argument("--raw", action="store_true", help="skip Tier-1 formatting")
    tr.add_argument("--dict", default=None, help="custom dictionary TOML (default: user config)")
    tr.add_argument("--inject", action="store_true", help="inject the transcript into focus")
    tr.add_argument("--method", default="auto", choices=["auto", "type", "paste"])
    tr.set_defaults(func=_cmd_transcribe)

    di = sub.add_parser("dictate", help="hold key -> speak -> release -> inject (the MVP)")
    di.add_argument("--engine", default="faster-whisper")
    di.add_argument("--model", default=None)
    di.add_argument("--device", default="cpu", choices=["cpu", "cuda", "auto"],
                    help="ASR compute device")
    di.add_argument("--compute-type", default="int8")
    di.add_argument("--no-vad", action="store_true")
    di.add_argument("--mode", choices=["hold", "toggle", "double_tap"], default="hold")
    di.add_argument("--key", default="ctrl_r")
    di.add_argument("--audio-device", default=None, help="mic device (default pulse/pipewire)")
    di.add_argument("--method", default="auto", choices=["auto", "type", "paste"])
    di.add_argument("--raw", action="store_true", help="skip Tier-1 formatting")
    di.add_argument("--dict", default=None, help="custom dictionary TOML (default: user config)")
    di.add_argument("--no-inject", action="store_true", help="print transcript, don't inject")
    di.add_argument("--once", action="store_true", help="transcribe one utterance then exit")
    di.add_argument("--no-feedback", action="store_true")
    di.add_argument("--save-audio", action="store_true", help="also save WAVs (off by default)")
    di.set_defaults(func=_cmd_dictate)

    sub.add_parser("setup", help="first-run TUI wizard (env, config, dictionary)").set_defaults(func=_cmd_setup)
    sub.add_parser("config", help="edit configuration (TUI)").set_defaults(func=_cmd_config)
    sub.add_parser("status", help="show config + daemon status").set_defaults(func=_cmd_status)
    sub.add_parser("start", help="run the dictation daemon (config-driven)").set_defaults(func=_cmd_start)
    sub.add_parser("stop", help="stop the systemd --user daemon").set_defaults(func=_cmd_stop)

    doc = sub.add_parser("doctor", help="diagnostics: injection + audio + hotkey + asr")
    doc.set_defaults(func=_cmd_doctor)

    ver = sub.add_parser("version", help="print version")
    ver.set_defaults(func=_cmd_version)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
