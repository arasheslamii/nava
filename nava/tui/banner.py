"""ASCII banner for the TUI (Rich)."""

from __future__ import annotations

from .. import __version__

LOGO = r"""
 ███╗   ██╗ █████╗ ██╗   ██╗ █████╗
 ████╗  ██║██╔══██╗██║   ██║██╔══██╗
 ██╔██╗ ██║███████║██║   ██║███████║
 ██║╚██╗██║██╔══██║╚██╗ ██╔╝██╔══██║
 ██║ ╚████║██║  ██║ ╚████╔╝ ██║  ██║
 ╚═╝  ╚═══╝╚═╝  ╚═╝  ╚═══╝  ╚═╝  ╚═╝
"""


def print_banner(console=None) -> None:
    from rich.console import Console
    from rich.text import Text

    console = console or Console()
    console.print(Text(LOGO, style="bold cyan"))
    console.print(Text(f"  NAVA {__version__} — local-first voice dictation for Linux",
                       style="dim"))
    console.print()
