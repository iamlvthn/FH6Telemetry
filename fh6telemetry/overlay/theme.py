"""Visual theme constants and small formatting helpers for the overlay."""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont

# --- Palette -----------------------------------------------------------------
BACKGROUND = QColor(12, 14, 18, 205)
PANEL_BG = QColor(22, 26, 32, 180)
BORDER = QColor(70, 78, 90, 160)
TEXT = QColor(235, 238, 242)
TEXT_DIM = QColor(150, 158, 168)
ACCENT = QColor(0, 200, 255)

THROTTLE = QColor(60, 220, 120)
BRAKE = QColor(235, 70, 70)
CLUTCH = QColor(240, 190, 60)

SHIFT_OK = QColor(70, 220, 120)
SHIFT_WARN = QColor(245, 200, 60)
SHIFT_CRIT = QColor(240, 60, 60)

DELTA_FASTER = QColor(70, 220, 120)
DELTA_SLOWER = QColor(240, 90, 90)

# Tyre temperature status -> colour.
TIRE_COLORS = {
    "cold": QColor(70, 130, 240),
    "warming": QColor(90, 200, 210),
    "optimal": QColor(70, 220, 120),
    "hot": QColor(245, 170, 50),
    "overheating": QColor(240, 60, 60),
}

# Handling balance.
UNDERSTEER = QColor(80, 150, 245)
OVERSTEER = QColor(245, 120, 60)
NEUTRAL = QColor(70, 220, 120)


def font(size: int, *, bold: bool = False, mono: bool = True) -> QFont:
    family = "Consolas" if mono else "Segoe UI"
    f = QFont(family, size)
    f.setBold(bold)
    if mono:
        f.setStyleHint(QFont.StyleHint.Monospace)
    return f


def lerp_color(a: QColor, b: QColor, t: float) -> QColor:
    t = max(0.0, min(1.0, t))
    return QColor(
        int(a.red() + (b.red() - a.red()) * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue() + (b.blue() - a.blue()) * t),
        int(a.alpha() + (b.alpha() - a.alpha()) * t),
    )


def format_time(seconds: float) -> str:
    """Format a lap time as ``M:SS.mmm`` (or ``--:--.---`` when unset)."""
    if seconds is None or seconds <= 0:
        return "--:--.---"
    minutes = int(seconds // 60)
    rem = seconds - minutes * 60
    return f"{minutes}:{rem:06.3f}"


def format_delta(seconds: float) -> str:
    sign = "+" if seconds >= 0 else "-"
    return f"{sign}{abs(seconds):.3f}"
