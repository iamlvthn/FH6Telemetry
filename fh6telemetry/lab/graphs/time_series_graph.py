"""Custom-painted time-series line graph for the Lab."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ...analytics.history import downsample_for_display
from ...overlay import theme


@dataclass(slots=True)
class GraphSeries:
    name: str
    xs: list[float]
    ys: list[float]
    color: QColor
    axis: str = "primary"  # primary | secondary


@dataclass(slots=True)
class GraphMarker:
    """Vertical marker (e.g. gear shift) at a given time."""

    x: float
    label: str
    color: QColor


class TimeSeriesGraph(QWidget):
    """Scrollable line chart with optional dual Y-axis and event markers."""

    def __init__(self, title: str = "", *, dual_axis: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title
        self._dual_axis = dual_axis
        self._series: list[GraphSeries] = []
        self._markers: list[GraphMarker] = []
        self._x_start: float | None = None
        self._x_end: float | None = None
        self._follow_live = True
        self._window_seconds = 30.0
        self._y_unit = ""
        self._y2_unit = ""
        self.setMinimumSize(320, 180)

    def set_title(self, title: str) -> None:
        self._title = title
        self.update()

    def set_y_unit(self, unit: str, *, secondary: str = "") -> None:
        self._y_unit = unit
        self._y2_unit = secondary
        self.update()

    def set_series(
        self,
        name: str,
        xs: list[float],
        ys: list[float],
        color: QColor,
        *,
        axis: str = "primary",
    ) -> None:
        for i, series in enumerate(self._series):
            if series.name == name:
                self._series[i] = GraphSeries(name, xs, ys, color, axis)
                self.update()
                return
        self._series.append(GraphSeries(name, xs, ys, color, axis))
        self.update()

    def set_markers(self, markers: list[GraphMarker]) -> None:
        self._markers = markers
        self.update()

    def clear_series(self) -> None:
        self._series.clear()
        self._markers.clear()
        self.update()

    def set_x_range(self, start: float, end: float) -> None:
        self._x_start = start
        self._x_end = end
        self._follow_live = False
        self.update()

    def set_follow_live(self, enabled: bool, *, window_seconds: float = 30.0) -> None:
        self._follow_live = enabled
        self._window_seconds = max(5.0, window_seconds)
        if enabled:
            self._x_start = None
            self._x_end = None
        self.update()

    def window_seconds(self) -> float:
        return self._window_seconds

    def set_window_seconds(self, seconds: float) -> None:
        self._window_seconds = max(5.0, seconds)

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(8, 8, self.width() - 16, self.height() - 16)
        painter.fillRect(rect, QColor(18, 22, 28, 240))
        painter.setPen(QPen(theme.BORDER, 1))
        painter.drawRoundedRect(rect, 8, 8)

        left_pad = 48
        right_pad = 48 if self._dual_axis else 8
        plot = QRectF(
            rect.left() + left_pad,
            rect.top() + 28,
            rect.width() - left_pad - right_pad,
            rect.height() - 44,
        )
        if plot.width() <= 0 or plot.height() <= 0:
            return

        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.setPen(theme.TEXT)
        painter.drawText(
            QRectF(rect.left() + 12, rect.top() + 8, rect.width() - 24, 16),
            Qt.AlignmentFlag.AlignLeft,
            self._title,
        )

        if not self._series:
            painter.setPen(theme.TEXT_DIM)
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(plot, Qt.AlignmentFlag.AlignCenter, "No data")
            return

        x_min, x_max = self._x_bounds()
        y_min, y_max, y2_min, y2_max = self._y_bounds()

        self._draw_grid(painter, plot, y_min, y_max, side="left")
        if self._dual_axis:
            self._draw_grid(painter, plot, y2_min, y2_max, side="right")

        for marker in self._markers:
            self._draw_marker(painter, plot, marker, x_min, x_max)

        for series in self._series:
            if series.axis == "secondary" and self._dual_axis:
                self._draw_series(painter, plot, series, x_min, x_max, y2_min, y2_max)
            else:
                self._draw_series(painter, plot, series, x_min, x_max, y_min, y_max)

        self._draw_legend(painter, rect)

    def _x_bounds(self) -> tuple[float, float]:
        x_min = float("inf")
        x_max = float("-inf")
        for series in self._series:
            for x in series.xs:
                if x < x_min:
                    x_min = x
                if x > x_max:
                    x_max = x

        if self._follow_live and x_max > x_min:
            x_min = max(0.0, x_max - self._window_seconds)
        elif self._x_start is not None and self._x_end is not None:
            x_min, x_max = self._x_start, self._x_end

        if x_min == float("inf"):
            x_min = 0.0
        if x_max == float("-inf"):
            x_max = 1.0
        if x_max <= x_min:
            x_max = x_min + 1.0
        return x_min, x_max

    def _y_bounds(self) -> tuple[float, float, float, float]:
        y_min = float("inf")
        y_max = float("-inf")
        y2_min = float("inf")
        y2_max = float("-inf")

        for series in self._series:
            for y in series.ys:
                if y != y:
                    continue
                if series.axis == "secondary" and self._dual_axis:
                    if y < y2_min:
                        y2_min = y
                    if y > y2_max:
                        y2_max = y
                else:
                    if y < y_min:
                        y_min = y
                    if y > y_max:
                        y_max = y

        if y_min == float("inf"):
            y_min = 0.0
        if y_max == float("-inf"):
            y_max = 1.0
        if y2_min == float("inf"):
            y2_min = 0.0
        if y2_max == float("-inf"):
            y2_max = 1.0

        y_pad = (y_max - y_min) * 0.08 or 1.0
        y_min -= y_pad
        y_max += y_pad
        y2_pad = (y2_max - y2_min) * 0.08 or 1.0
        y2_min -= y2_pad
        y2_max += y2_pad
        return y_min, y_max, y2_min, y2_max

    def _draw_grid(self, painter: QPainter, plot: QRectF, y_min: float, y_max: float, *, side: str) -> None:
        painter.setPen(QPen(QColor(50, 56, 66, 180), 1))
        if side == "left":
            for i in range(5):
                y = plot.top() + plot.height() * i / 4.0
                painter.drawLine(plot.left(), y, plot.right(), y)
            painter.drawLine(plot.left(), plot.top(), plot.left(), plot.bottom())

        painter.setFont(theme.font(7))
        painter.setPen(theme.TEXT_DIM)
        for i in range(5):
            value = y_max - (y_max - y_min) * i / 4.0
            y = plot.top() + plot.height() * i / 4.0
            if side == "left":
                painter.drawText(
                    QRectF(plot.left() - 46, y - 6, 42, 12),
                    Qt.AlignmentFlag.AlignRight,
                    f"{value:0.0f}",
                )
            else:
                painter.drawText(
                    QRectF(plot.right() + 4, y - 6, 42, 12),
                    Qt.AlignmentFlag.AlignLeft,
                    f"{value:0.0f}",
                )

    def _draw_marker(
        self,
        painter: QPainter,
        plot: QRectF,
        marker: GraphMarker,
        x_min: float,
        x_max: float,
    ) -> None:
        if marker.x < x_min or marker.x > x_max:
            return
        x_span = x_max - x_min
        px = plot.left() + (marker.x - x_min) / x_span * plot.width()
        painter.setPen(QPen(marker.color, 1, Qt.PenStyle.DashLine))
        painter.drawLine(px, plot.top(), px, plot.bottom())

    def _draw_series(
        self,
        painter: QPainter,
        plot: QRectF,
        series: GraphSeries,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
    ) -> None:
        xs, ys = downsample_for_display(series.xs, series.ys)
        if len(xs) < 2:
            return

        x_span = x_max - x_min
        y_span = y_max - y_min
        points: list[tuple[float, float]] = []
        for x, y in zip(xs, ys, strict=False):
            if y != y:
                continue
            px = plot.left() + (x - x_min) / x_span * plot.width()
            py = plot.bottom() - (y - y_min) / y_span * plot.height()
            points.append((px, py))

        if len(points) < 2:
            return

        painter.setPen(QPen(series.color, 2))
        for i in range(1, len(points)):
            painter.drawLine(points[i - 1][0], points[i - 1][1], points[i][0], points[i][1])

    def _draw_legend(self, painter: QPainter, rect: QRectF) -> None:
        if not self._series:
            return
        painter.setFont(theme.font(7, mono=False))
        x = rect.right() - 12
        y = rect.top() + 10
        for series in reversed(self._series):
            label = series.name
            metrics = painter.fontMetrics()
            width = metrics.horizontalAdvance(label) + 14
            x -= width
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(series.color)
            painter.drawRoundedRect(x, y, 8, 8, 2, 2)
            painter.setPen(theme.TEXT_DIM)
            painter.drawText(x + 11, y + 8, label)
