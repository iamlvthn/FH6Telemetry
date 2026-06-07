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


class TimeSeriesGraph(QWidget):
    """Scrollable line chart with optional live follow and manual X range."""

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title
        self._series: list[GraphSeries] = []
        self._x_start: float | None = None
        self._x_end: float | None = None
        self._follow_live = True
        self._window_seconds = 30.0
        self._y_unit = ""
        self.setMinimumSize(400, 220)

    def set_title(self, title: str) -> None:
        self._title = title
        self.update()

    def set_y_unit(self, unit: str) -> None:
        self._y_unit = unit
        self.update()

    def set_series(self, name: str, xs: list[float], ys: list[float], color: QColor) -> None:
        """Replace or add a named series."""
        for i, series in enumerate(self._series):
            if series.name == name:
                self._series[i] = GraphSeries(name, xs, ys, color)
                self.update()
                return
        self._series.append(GraphSeries(name, xs, ys, color))
        self.update()

    def clear_series(self) -> None:
        self._series.clear()
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

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(8, 8, self.width() - 16, self.height() - 16)
        painter.fillRect(rect, QColor(18, 22, 28, 240))
        painter.setPen(QPen(theme.BORDER, 1))
        painter.drawRoundedRect(rect, 8, 8)

        plot = QRectF(rect.left() + 48, rect.top() + 28, rect.width() - 56, rect.height() - 44)
        if plot.width() <= 0 or plot.height() <= 0:
            return

        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.setPen(theme.TEXT)
        painter.drawText(QRectF(rect.left() + 12, rect.top() + 8, rect.width() - 24, 16),
                         Qt.AlignmentFlag.AlignLeft, self._title)

        if not self._series:
            painter.setPen(theme.TEXT_DIM)
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(plot, Qt.AlignmentFlag.AlignCenter, "No data")
            return

        x_min, x_max, y_min, y_max = self._value_bounds()
        if x_max <= x_min:
            x_max = x_min + 1.0
        if y_max <= y_min:
            y_max = y_min + 1.0
        y_pad = (y_max - y_min) * 0.08 or 1.0
        y_min -= y_pad
        y_max += y_pad

        self._draw_grid(painter, plot, y_min, y_max)
        for series in self._series:
            self._draw_series(painter, plot, series, x_min, x_max, y_min, y_max)

        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(theme.TEXT_DIM)
        unit = f" {self._y_unit}" if self._y_unit else ""
        painter.drawText(QRectF(plot.left(), plot.bottom() + 4, plot.width(), 12),
                         Qt.AlignmentFlag.AlignRight, f"{y_max:0.0f}{unit}")

    def _value_bounds(self) -> tuple[float, float, float, float]:
        x_min = float("inf")
        x_max = float("-inf")
        y_min = float("inf")
        y_max = float("-inf")

        for series in self._series:
            for x, y in zip(series.xs, series.ys, strict=False):
                if x < x_min:
                    x_min = x
                if x > x_max:
                    x_max = x
                if y != y:  # skip NaN
                    continue
                if y < y_min:
                    y_min = y
                if y > y_max:
                    y_max = y

        if self._follow_live and x_max > x_min:
            x_min = max(0.0, x_max - self._window_seconds)
        elif self._x_start is not None and self._x_end is not None:
            x_min, x_max = self._x_start, self._x_end

        if x_min == float("inf"):
            x_min = 0.0
        if x_max == float("-inf"):
            x_max = 1.0
        if y_min == float("inf"):
            y_min = 0.0
        if y_max == float("-inf"):
            y_max = 1.0
        return x_min, x_max, y_min, y_max

    def _draw_grid(self, painter: QPainter, plot: QRectF, y_min: float, y_max: float) -> None:
        painter.setPen(QPen(QColor(50, 56, 66, 180), 1))
        for i in range(5):
            y = plot.top() + plot.height() * i / 4.0
            painter.drawLine(plot.left(), y, plot.right(), y)
        painter.drawLine(plot.left(), plot.top(), plot.left(), plot.bottom())

        painter.setFont(theme.font(7))
        painter.setPen(theme.TEXT_DIM)
        for i in range(5):
            value = y_max - (y_max - y_min) * i / 4.0
            y = plot.top() + plot.height() * i / 4.0
            painter.drawText(QRectF(plot.left() - 46, y - 6, 42, 12),
                             Qt.AlignmentFlag.AlignRight, f"{value:0.0f}")

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
