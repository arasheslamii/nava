"""Rich-rendered diagnostics panel."""

from __future__ import annotations

from ..diagnostics.checks import Check, run_all


def render_diagnostics(console=None, checks: list[Check] | None = None) -> bool:
    from rich.console import Console
    from rich.table import Table

    console = console or Console()
    checks = checks if checks is not None else run_all()

    table = Table(title="NAVA diagnostics", title_style="bold", header_style="bold")
    table.add_column("check", no_wrap=True)
    table.add_column("status", no_wrap=True)
    table.add_column("detail", overflow="fold")
    for c in checks:
        if c.ok:
            badge = "[green]✓ ok[/]"
        elif c.required:
            badge = "[red]✗ FAIL[/]"
        else:
            badge = "[yellow]· absent[/]"
        table.add_row(c.name, badge, c.detail)
    console.print(table)

    failed = [c for c in checks if c.required and not c.ok]
    if failed:
        console.print(f"[red]✗ {len(failed)} required check(s) failing.[/] "
                      "Run the installer or fix the above before dictating.")
        return False
    console.print("[green]✓ all required checks passing — ready to dictate.[/]")
    return True
