"""`flowlinux-inject` — CLI entry point for the M1 injection spike."""

from __future__ import annotations

import argparse
import sys
import time

from .injection.manager import InjectionManager
from .injection.preflight import (
    apt_install_hint,
    check_dependencies,
    missing_required,
    session_is_x11,
)
from .injection.window import get_active_window


def _cmd_doctor() -> int:
    print("FlowLinux injection diagnostics")
    x11 = session_is_x11()
    print(f"  session is X11 : {'yes' if x11 else 'NO (Wayland backend not yet implemented)'}")
    for dep, ok in check_dependencies():
        flag = "ok     " if ok else ("MISSING" if dep.required else "absent ")
        req = "required" if dep.required else "optional"
        print(f"  [{flag}] {dep.name:<12} ({req}) - {dep.purpose}")
    win = get_active_window()
    if win:
        kind = "terminal" if win.is_terminal else "normal"
        print(f"  active window  : class={win.wm_class!r} ({kind}) id={win.window_id}")
    else:
        print("  active window  : could not detect (xdotool missing or no X11?)")
    print("  backend health :")
    for h in InjectionManager().health():
        print(f"    [{'ok ' if h.ok else 'bad'}] {h.backend:<7} - {h.detail}")
    miss = missing_required()
    if miss:
        print("\n  Install missing required deps:")
        print("    " + apt_install_hint(miss))
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="flowlinux-inject",
        description="Inject text into the focused window (X11). Reads stdin if no text given.",
    )
    p.add_argument("text", nargs="*", help="text to inject; if omitted, read from stdin")
    p.add_argument("--method", choices=["auto", "type", "paste"], default="auto",
                   help="auto (type, then fall back), type (XTEST), or paste (clipboard)")
    p.add_argument("--paste", action="store_true", help="shortcut for --method paste")
    p.add_argument("--wait", type=float, default=0.0, metavar="SEC",
                   help="wait before injecting, to focus another window")
    p.add_argument("--delay", type=int, default=12, metavar="MS",
                   help="xdotool inter-key delay (type mode)")
    p.add_argument("--no-restore", action="store_true",
                   help="don't restore the previous clipboard after paste")
    p.add_argument("--doctor", action="store_true", help="run diagnostics and exit")
    args = p.parse_args(argv)

    if args.doctor:
        return _cmd_doctor()

    text = " ".join(args.text) if args.text else sys.stdin.read()
    text = text.rstrip("\n")  # drop the trailing newline `echo` adds
    if not text:
        print("flowlinux-inject: no input text", file=sys.stderr)
        return 2

    method = "paste" if args.paste else args.method

    miss = missing_required()
    if miss:
        print("flowlinux-inject: missing required deps: "
              + ", ".join(d.name for d in miss), file=sys.stderr)
        print("  " + apt_install_hint(miss), file=sys.stderr)
        # still attempt — the notify fallback may still recover the text

    if args.wait > 0:
        time.sleep(args.wait)

    mgr = InjectionManager(delay_ms=args.delay, restore_clipboard=not args.no_restore)
    res = mgr.inject(text, method=method)
    if res.ok:
        extra = f" (after {', '.join(res.fallbacks)})" if res.fallbacks else ""
        print(f"flowlinux-inject: ok via {res.backend} - {res.detail}{extra}", file=sys.stderr)
        return 0
    print(f"flowlinux-inject: FAILED - {res.detail}; tried: {', '.join(res.fallbacks)}",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
