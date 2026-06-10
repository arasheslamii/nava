"""Global hotkey (M2).

`base.py`: PTTController state machine (hold/toggle/double-tap, pure + unit-tested).
`pynput_x11.py`: PynputX11Hotkey — X11 key monitor (Right-Ctrl PTT, no grab needed),
collapsing OS auto-repeat into single edges. An EvdevHotkey for future Wayland slots
in behind the same shape.
"""
