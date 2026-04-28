"""Helpers for keeping native window chrome aligned with the app theme."""
from __future__ import annotations

import ctypes
import sys

from PyQt6.QtCore import QEvent, QObject

from config import COLORS, is_dark_theme


DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_BORDER_COLOR = 34
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36


def _colorref(hex_color: str) -> int:
    """Convert #RRGGBB into the 0x00BBGGRR COLORREF format used by Win32."""
    value = hex_color.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Expected #RRGGBB color, got {hex_color!r}")

    red = int(value[0:2], 16)
    green = int(value[2:4], 16)
    blue = int(value[4:6], 16)
    return red | (green << 8) | (blue << 16)


def apply_dark_title_bar(
    widget,
    background: str | None = None,
    text: str | None = None,
    border: str | None = None,
) -> bool:
    """Apply the app's dark palette to a native Windows title bar when available."""
    background = background or COLORS["background"]
    text = text or COLORS["text_dark"]
    border = border or COLORS["border"]

    widget.setProperty("usesDarkTitleBar", is_dark_theme())
    widget.setProperty("titleBarBackgroundColor", background)
    widget.setProperty("titleBarTextColor", text)
    widget.setProperty("titleBarBorderColor", border)

    if not hasattr(widget, "_dark_title_bar_event_filter"):
        event_filter = _DarkTitleBarEventFilter(widget)
        widget._dark_title_bar_event_filter = event_filter
        widget.installEventFilter(event_filter)

    return _apply_windows_dwm_theme(widget)


class _DarkTitleBarEventFilter(QObject):
    def eventFilter(self, obj, event):  # noqa: N802 - Qt API name
        if event.type() in (QEvent.Type.Show, QEvent.Type.WinIdChange):
            _apply_windows_dwm_theme(obj)
        return False


def _apply_windows_dwm_theme(widget) -> bool:
    if sys.platform != "win32":
        return False

    try:
        hwnd = int(widget.winId())
        if not hwnd:
            return False

        dwmapi = ctypes.windll.dwmapi
        applied = _set_dwm_bool(
            dwmapi,
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            bool(widget.property("usesDarkTitleBar")),
        )
        if not applied:
            applied = _set_dwm_bool(
                dwmapi,
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1,
                bool(widget.property("usesDarkTitleBar")),
            )

        _set_dwm_color(dwmapi, hwnd, DWMWA_CAPTION_COLOR, widget.property("titleBarBackgroundColor"))
        _set_dwm_color(dwmapi, hwnd, DWMWA_TEXT_COLOR, widget.property("titleBarTextColor"))
        _set_dwm_color(dwmapi, hwnd, DWMWA_BORDER_COLOR, widget.property("titleBarBorderColor"))
        return applied
    except (AttributeError, OSError, RuntimeError, TypeError, ValueError):
        return False


def _set_dwm_bool(dwmapi, hwnd: int, attribute: int, enabled: bool) -> bool:
    value = ctypes.c_int(1 if enabled else 0)
    return (
        dwmapi.DwmSetWindowAttribute(
            hwnd,
            attribute,
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
        == 0
    )


def _set_dwm_color(dwmapi, hwnd: int, attribute: int, color: str) -> bool:
    value = ctypes.c_uint(_colorref(color))
    return (
        dwmapi.DwmSetWindowAttribute(
            hwnd,
            attribute,
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
        == 0
    )
