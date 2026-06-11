"""Terminal UI — Rich + questionary (M5). No GUI.

Styled installer/first-run wizard (`run_setup`), config editor (`run_config_editor`),
diagnostics panel (`render_diagnostics`), and banner. A graphical window was rejected
(ADR-0007) in favor of a terminal-first UX.
"""

from .banner import print_banner
from .diagnostics import render_diagnostics
from .wizard import apply_answers, run_config_editor, run_setup

__all__ = ["print_banner", "render_diagnostics", "run_setup", "run_config_editor", "apply_answers"]
