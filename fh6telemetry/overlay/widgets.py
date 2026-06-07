"""Custom-painted HUD panels.

Each panel is a self-contained ``QWidget`` that renders one group of related
metrics from a :class:`~fh6telemetry.models.HudState`. Panels never compute
anything: they only translate already-derived values into pixels, which keeps
the rendering layer trivial to reason about and re-style.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QWidget

from ..models import HudState
from . import theme

# Compact horizontal strip geometry (single bottom row).
CELL_W = 118
ROW_H = 88
SPACING = 5

# Per-panel widths tuned for a left-to-right driving HUD.
CORE_W = 200
LAPS_W = 128
PERF_W = 175
HANDLING_W = 145


class BasePanel(QWidget):
    """Common background/styling and state plumbing for every panel."""

    def __init__(self, width: int = CELL_W, height: int = ROW_H) -> None:
        super().__init__()
        self.setFixedSize(width, height)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._state = HudState()
        self.use_metric = True
        self.blink = False

    def set_state(self, state: HudState, metric: bool, blink: bool = False) -> None:
        self._state = state
        self.use_metric = metric
        self.blink = blink
        self.update()

    # -- shared drawing helpers -------------------------------------------------
    def _begin(self) -> QPainter:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        painter.fillPath(path, QBrush(theme.PANEL_BG))
        painter.setPen(QPen(theme.BORDER, 1))
        painter.drawPath(path)
        return painter

    def _label(self, painter: QPainter, text: str, x: float, y: float) -> None:
        painter.setFont(theme.font(7, mono=False))
        painter.setPen(theme.TEXT_DIM)
        painter.drawText(QRectF(x, y, self.width() - x, 12), Qt.AlignmentFlag.AlignLeft, text)


class CorePanel(BasePanel):
    """Gear, RPM bar with shift light, and speed - the centrepiece."""

    def __init__(self) -> None:
        super().__init__(CORE_W, ROW_H)

    def paintEvent(self, _event) -> None:
        s = self._state
        painter = self._begin()
        w = self.width()

        # RPM bar across the top.
        bar = QRectF(10, 8, w - 20, 10)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(40, 44, 52, 200))
        painter.drawRoundedRect(bar, 3, 3)

        if s.shift_light < 0.5:
            color = theme.lerp_color(theme.SHIFT_OK, theme.SHIFT_WARN, s.shift_light * 2)
        else:
            color = theme.lerp_color(theme.SHIFT_WARN, theme.SHIFT_CRIT, (s.shift_light - 0.5) * 2)
        if s.should_shift and self.blink:
            color = theme.SHIFT_CRIT
        fill = QRectF(bar)
        fill.setWidth(bar.width() * max(0.0, min(1.0, s.rpm_fraction)))
        painter.setBrush(color)
        painter.drawRoundedRect(fill, 3, 3)

        # Gear (large, left).
        gear_text = "R" if s.gear == 0 else str(s.gear)
        painter.setFont(theme.font(34, bold=True))
        painter.setPen(theme.SHIFT_CRIT if s.should_shift and self.blink else theme.TEXT)
        painter.drawText(QRectF(8, 22, 68, 52), Qt.AlignmentFlag.AlignCenter, gear_text)
        self._label(painter, "GEAR", 8, 74)

        # Speed (large, right).
        speed = s.speed_kph if self.use_metric else s.speed_mph
        unit = "km/h" if self.use_metric else "mph"
        painter.setFont(theme.font(28, bold=True))
        painter.setPen(theme.TEXT)
        painter.drawText(QRectF(78, 24, w - 86, 42), Qt.AlignmentFlag.AlignRight, f"{speed:0.0f}")
        painter.setFont(theme.font(8, mono=False))
        painter.setPen(theme.TEXT_DIM)
        painter.drawText(QRectF(78, 64, w - 84, 14), Qt.AlignmentFlag.AlignRight, unit)

        # RPM readout (small, right under bar).
        painter.setFont(theme.font(7, mono=False))
        painter.setPen(theme.TEXT_DIM)
        painter.drawText(
            QRectF(78, 22, w - 84, 10),
            Qt.AlignmentFlag.AlignRight,
            f"{s.rpm:0.0f} rpm",
        )


class InputsPanel(BasePanel):
    """Vertical throttle/brake/clutch bars plus a steering indicator."""

    def paintEvent(self, _event) -> None:
        s = self._state
        painter = self._begin()
        self._label(painter, "INPUTS", 10, 6)

        bars = [
            ("T", s.throttle, theme.THROTTLE),
            ("B", s.brake, theme.BRAKE),
            ("C", s.clutch, theme.CLUTCH),
        ]
        bar_w = 20
        gap = 8
        total = len(bars) * bar_w + (len(bars) - 1) * gap
        x0 = (self.width() - total) / 2
        top = 18
        bottom = 66
        height = bottom - top

        for i, (label, value, color) in enumerate(bars):
            x = x0 + i * (bar_w + gap)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(40, 44, 52, 200))
            painter.drawRoundedRect(QRectF(x, top, bar_w, height), 3, 3)
            fh = height * max(0.0, min(1.0, value))
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(x, bottom - fh, bar_w, fh), 3, 3)
            painter.setFont(theme.font(7, mono=False))
            painter.setPen(theme.TEXT_DIM)
            painter.drawText(QRectF(x, bottom + 2, bar_w, 12), Qt.AlignmentFlag.AlignCenter, label)

        # Steering indicator at the very bottom.
        track = QRectF(10, self.height() - 8, self.width() - 20, 4)
        painter.setBrush(QColor(40, 44, 52, 200))
        painter.drawRoundedRect(track, 2, 2)
        cx = track.center().x() + (track.width() / 2) * max(-1.0, min(1.0, s.steer))
        painter.setBrush(theme.ACCENT)
        painter.drawEllipse(cx - 3, track.center().y() - 3, 6, 6)


class PowerPanel(BasePanel):
    """Power, torque, boost, drivetrain and fuel."""

    def paintEvent(self, _event) -> None:
        s = self._state
        painter = self._begin()
        self._label(painter, "ENGINE", 10, 6)

        # Horsepower is the most widely recognised figure; show it prominently.
        painter.setFont(theme.font(18, bold=True))
        painter.setPen(theme.TEXT)
        painter.drawText(QRectF(8, 16, self.width() - 16, 22), Qt.AlignmentFlag.AlignLeft, f"{s.power_hp:0.0f}")
        painter.setFont(theme.font(7, mono=False))
        painter.setPen(theme.TEXT_DIM)
        painter.drawText(QRectF(8, 24, self.width() - 12, 12), Qt.AlignmentFlag.AlignRight, "hp")

        painter.setFont(theme.font(7, mono=False))
        rows = [
            ("Trq", f"{s.torque_nm:0.0f}"),
            ("Bst", f"{s.boost_psi:0.1f}"),
            ("Drv", s.drivetrain),
        ]
        y = 40
        for label, value in rows:
            painter.setPen(theme.TEXT_DIM)
            painter.drawText(QRectF(8, y, 28, 12), Qt.AlignmentFlag.AlignLeft, label)
            painter.setPen(theme.TEXT)
            painter.drawText(QRectF(self.width() - 72, y, 64, 12), Qt.AlignmentFlag.AlignRight, value)
            y += 12

        # Fuel bar.
        track = QRectF(8, self.height() - 10, self.width() - 16, 4)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(40, 44, 52, 200))
        painter.drawRoundedRect(track, 2, 2)
        fill = QRectF(track)
        fill.setWidth(track.width() * max(0.0, min(1.0, s.fuel_fraction)))
        painter.setBrush(theme.ACCENT)
        painter.drawRoundedRect(fill, 2, 2)


class GForcePanel(BasePanel):
    """Traction circle with live and peak g-force."""

    def paintEvent(self, _event) -> None:
        s = self._state
        painter = self._begin()
        self._label(painter, "G-FORCE", 10, 6)

        cx = self.width() / 2
        cy = self.height() / 2 + 2
        radius = 28
        scale = radius / 1.5  # 1.5 g maps to the rim

        painter.setPen(QPen(theme.BORDER, 1))
        painter.setBrush(QColor(30, 34, 40, 160))
        painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)
        painter.setPen(QPen(QColor(70, 78, 90, 120), 1))
        painter.drawLine(cx - radius, cy, cx + radius, cy)
        painter.drawLine(cx, cy - radius, cx, cy + radius)

        # Peak ring.
        peak_r = min(radius, s.g_peak * scale)
        if peak_r > 1:
            painter.setPen(QPen(theme.TEXT_DIM, 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(cx - peak_r, cy - peak_r, peak_r * 2, peak_r * 2)

        # Live dot: +lat right, +long forward = up.
        dx = max(-radius, min(radius, s.g_lat * scale))
        dy = max(-radius, min(radius, -s.g_long * scale))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(theme.ACCENT)
        painter.drawEllipse(cx + dx - 4, cy + dy - 4, 8, 8)

        painter.setFont(theme.font(8, mono=False))
        painter.setPen(theme.TEXT)
        painter.drawText(QRectF(6, self.height() - 14, self.width() - 12, 11),
                         Qt.AlignmentFlag.AlignLeft, f"{s.g_total:0.2f}g")
        painter.setPen(theme.TEXT_DIM)
        painter.drawText(QRectF(6, self.height() - 14, self.width() - 12, 11),
                         Qt.AlignmentFlag.AlignRight, f"pk {s.g_peak:0.2f}")


class TiresPanel(BasePanel):
    """Four-corner tyre temperatures and combined-slip indicators."""

    def paintEvent(self, _event) -> None:
        s = self._state
        painter = self._begin()
        self._label(painter, "TYRES °" + ("C" if self.use_metric else "F"), 10, 6)

        cell_w = 38
        cell_h = 24
        gap_x = 10
        gap_y = 5
        x0 = (self.width() - (cell_w * 2 + gap_x)) / 2
        y0 = 18
        # FL, FR, RL, RR -> grid positions.
        positions = [(0, 0), (1, 0), (0, 1), (1, 1)]
        for idx, (col, row) in enumerate(positions):
            temp_c = s.tire_temp_c[idx]
            temp = temp_c if self.use_metric else temp_c * 9 / 5 + 32
            status = s.tire_status[idx]
            color = theme.TIRE_COLORS.get(status, theme.TEXT_DIM)
            x = x0 + col * (cell_w + gap_x)
            y = y0 + row * (cell_h + gap_y)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(x, y, cell_w, cell_h), 4, 4)
            painter.setFont(theme.font(9, bold=True))
            painter.setPen(QColor(10, 12, 16))
            painter.drawText(QRectF(x, y, cell_w, cell_h - 8), Qt.AlignmentFlag.AlignCenter, f"{temp:0.0f}")
            # Slip indicator strip under each tyre.
            slip = max(0.0, min(1.0, s.tire_slip[idx]))
            strip = QRectF(x + 4, y + cell_h - 6, cell_w - 8, 3)
            painter.setBrush(QColor(10, 12, 16, 160))
            painter.drawRoundedRect(strip, 1, 1)
            sfill = QRectF(strip)
            sfill.setWidth(strip.width() * slip)
            painter.setBrush(QColor(20, 20, 20) if slip < 1 else theme.SHIFT_CRIT)
            painter.drawRoundedRect(sfill, 1, 1)


class HandlingPanel(BasePanel):
    """Understeer/oversteer balance bar."""

    def __init__(self) -> None:
        super().__init__(HANDLING_W, ROW_H)

    def paintEvent(self, _event) -> None:
        s = self._state
        painter = self._begin()
        self._label(painter, "BALANCE", 8, 6)

        painter.setFont(theme.font(6, mono=False))
        painter.setPen(theme.UNDERSTEER)
        painter.drawText(QRectF(8, 20, 50, 10), Qt.AlignmentFlag.AlignLeft, "PUSH")
        painter.setPen(theme.OVERSTEER)
        painter.drawText(QRectF(self.width() - 58, 20, 50, 10), Qt.AlignmentFlag.AlignRight, "LOOSE")

        track = QRectF(10, 38, self.width() - 20, 8)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(40, 44, 52, 200))
        painter.drawRoundedRect(track, 4, 4)

        center = track.center().x()
        value = max(-1.0, min(1.0, s.balance))
        half = track.width() / 2
        if s.balance_label == "understeer":
            color = theme.UNDERSTEER
        elif s.balance_label == "oversteer":
            color = theme.OVERSTEER
        else:
            color = theme.NEUTRAL

        if value >= 0:
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(center, track.top(), half * value, track.height()), 4, 4)
        else:
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(center + half * value, track.top(), -half * value, track.height()), 4, 4)

        painter.setPen(QPen(theme.TEXT, 1))
        painter.drawLine(center, track.top() - 2, center, track.bottom() + 2)

        painter.setFont(theme.font(7, mono=False))
        painter.setPen(theme.TEXT_DIM)
        painter.drawText(
            QRectF(8, self.height() - 16, self.width() - 16, 12),
            Qt.AlignmentFlag.AlignCenter,
            s.balance_label.upper(),
        )


class LapsPanel(BasePanel):
    """Lap counter, position, lap times and predictive delta."""

    def __init__(self) -> None:
        super().__init__(LAPS_W, ROW_H)

    def paintEvent(self, _event) -> None:
        s = self._state
        painter = self._begin()
        self._label(painter, f"LAP {s.lap_number}   P{s.race_position}", 10, 6)

        rows = [
            ("CUR", theme.format_time(s.current_lap)),
            ("LAST", theme.format_time(s.last_lap)),
            ("BEST", theme.format_time(s.best_lap)),
        ]
        y = 18
        painter.setFont(theme.font(8))
        for label, value in rows:
            painter.setPen(theme.TEXT_DIM)
            painter.drawText(QRectF(8, y, 34, 12), Qt.AlignmentFlag.AlignLeft, label)
            painter.setPen(theme.TEXT)
            painter.drawText(QRectF(36, y, self.width() - 44, 12), Qt.AlignmentFlag.AlignRight, value)
            y += 13

        # Delta (prominent).
        if s.delta_valid:
            color = theme.DELTA_FASTER if s.delta < 0 else theme.DELTA_SLOWER
            text = theme.format_delta(s.delta)
        else:
            color = theme.TEXT_DIM
            text = "--.---"
        painter.setFont(theme.font(11, bold=True))
        painter.setPen(color)
        painter.drawText(QRectF(8, self.height() - 22, self.width() - 16, 16),
                         Qt.AlignmentFlag.AlignRight, text)
        painter.setFont(theme.font(7, mono=False))
        painter.setPen(theme.TEXT_DIM)
        painter.drawText(QRectF(8, self.height() - 20, 50, 12), Qt.AlignmentFlag.AlignLeft, "DELTA")


class PerformancePanel(BasePanel):
    """Acceleration runs and session records."""

    def __init__(self) -> None:
        super().__init__(PERF_W, ROW_H)

    def paintEvent(self, _event) -> None:
        s = self._state
        painter = self._begin()
        self._label(painter, "PERF", 8, 6)

        top = s.top_speed_kph if self.use_metric else s.top_speed_kph * 0.621371
        unit = "km/h" if self.use_metric else "mph"
        painter.setFont(theme.font(7, mono=False))
        painter.setPen(theme.TEXT_DIM)
        painter.drawText(QRectF(8, 18, 52, 11), Qt.AlignmentFlag.AlignLeft, "Top")
        painter.setPen(theme.TEXT)
        painter.drawText(QRectF(8, 18, self.width() - 16, 11), Qt.AlignmentFlag.AlignRight, f"{top:0.0f} {unit}")

        painter.setPen(theme.TEXT_DIM)
        painter.drawText(QRectF(8, 30, 52, 11), Qt.AlignmentFlag.AlignLeft, "Pwr")
        painter.setPen(theme.TEXT)
        painter.drawText(QRectF(8, 30, self.width() - 16, 11), Qt.AlignmentFlag.AlignRight, f"{s.max_power_hp:0.0f} hp")

        # Acceleration runs in a single horizontal row of chips.
        runs = list(s.accel_runs)[:4]
        painter.setFont(theme.font(7))
        chip_w = (self.width() - 16 - max(0, len(runs) - 1) * 4) / max(1, len(runs))
        x = 8
        y = 46
        for label, seconds in runs:
            painter.setPen(theme.TEXT_DIM)
            painter.drawText(QRectF(x, y, chip_w, 10), Qt.AlignmentFlag.AlignLeft, label)
            painter.setPen(theme.TEXT)
            painter.drawText(QRectF(x, y + 11, chip_w, 10), Qt.AlignmentFlag.AlignLeft, f"{seconds:0.1f}s")
            x += chip_w + 4

        if s.active_run_label:
            painter.setFont(theme.font(7, mono=False))
            painter.setPen(theme.ACCENT)
            painter.drawText(QRectF(8, self.height() - 13, self.width() - 16, 11),
                             Qt.AlignmentFlag.AlignLeft, f"{s.active_run_label}...")
