"""Multi-graph dashboard with shared timeline scrubber."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ...analytics.history import extract_channel, extract_shift_markers
from ...models import TimeSeriesSample
from ...overlay import theme
from .time_series_graph import GraphMarker, TimeSeriesGraph

_WINDOW_OPTIONS = [
    ("15 s", 15.0),
    ("30 s", 30.0),
    ("60 s", 60.0),
    ("120 s", 120.0),
]


class GraphWorkspace(QWidget):
    """2×2 graph grid plus delta/balance row and a shared timeline scrubber."""

    def __init__(self, *, metric: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._metric = metric
        self._follow_live = True
        self._elapsed = 0.0
        self._window_seconds = 30.0
        self._slider_busy = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        grid = QGridLayout()
        grid.setSpacing(8)

        unit = "km/h" if self._metric else "mph"
        temp_unit = "°C" if self._metric else "°F"

        self._speed = TimeSeriesGraph(f"Speed ({unit})")
        self._speed.set_y_unit(unit)

        self._power_rpm = TimeSeriesGraph("Power / RPM", dual_axis=True)
        self._power_rpm.set_y_unit("hp", secondary="rpm")

        self._gforce = TimeSeriesGraph("G-Force")
        self._gforce.set_y_unit("g")

        self._tyres = TimeSeriesGraph(f"Tyre temps ({temp_unit})")
        self._tyres.set_y_unit(temp_unit)

        self._delta_balance = TimeSeriesGraph("Lap delta / Handling balance", dual_axis=True)
        self._delta_balance.set_y_unit("s", secondary="bal")

        for graph in (
            self._speed,
            self._power_rpm,
            self._gforce,
            self._tyres,
            self._delta_balance,
        ):
            graph.set_follow_live(True, window_seconds=self._window_seconds)

        grid.addWidget(self._speed, 0, 0)
        grid.addWidget(self._power_rpm, 0, 1)
        grid.addWidget(self._gforce, 1, 0)
        grid.addWidget(self._tyres, 1, 1)
        layout.addLayout(grid, stretch=1)
        layout.addWidget(self._delta_balance)

        controls = QHBoxLayout()
        self._follow_check = QCheckBox("Follow live")
        self._follow_check.setChecked(True)
        self._follow_check.toggled.connect(self._on_follow_toggled)
        controls.addWidget(self._follow_check)

        controls.addWidget(QLabel("Window"))
        self._window_combo = QComboBox()
        for label, value in _WINDOW_OPTIONS:
            self._window_combo.addItem(label, value)
        self._window_combo.setCurrentIndex(1)
        self._window_combo.currentIndexChanged.connect(self._on_window_changed)
        controls.addWidget(self._window_combo)

        controls.addWidget(QLabel("Timeline"))
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setEnabled(False)
        self._slider.valueChanged.connect(self._on_slider_changed)
        controls.addWidget(self._slider, stretch=1)

        self._time_label = QLabel("0.0 s")
        self._time_label.setStyleSheet(
            f"color: rgb({theme.TEXT_DIM.red()}, {theme.TEXT_DIM.green()}, {theme.TEXT_DIM.blue()});"
        )
        controls.addWidget(self._time_label)
        layout.addLayout(controls)

        self._graphs = (
            self._speed,
            self._power_rpm,
            self._gforce,
            self._tyres,
            self._delta_balance,
        )

    @property
    def follow_live(self) -> bool:
        return self._follow_live

    def set_metric(self, metric: bool) -> None:
        self._metric = metric
        unit = "km/h" if metric else "mph"
        temp_unit = "°C" if metric else "°F"
        self._speed.set_title(f"Speed ({unit})")
        self._speed.set_y_unit(unit)
        self._tyres.set_title(f"Tyre temps ({temp_unit})")
        self._tyres.set_y_unit(temp_unit)

    def clear(self) -> None:
        for graph in self._graphs:
            graph.clear_series()
        self._elapsed = 0.0
        self._slider.setValue(0)
        self._time_label.setText("0.0 s")

    def refresh(
        self,
        samples: Sequence[TimeSeriesSample],
        *,
        compare_samples: Sequence[TimeSeriesSample] | None = None,
    ) -> None:
        if not samples:
            self.clear()
            return

        self._elapsed = samples[-1].t
        metric = self._metric

        xs, ys = extract_channel(samples, "speed", metric=metric)
        self._speed.set_series("speed", xs, ys, theme.ACCENT)
        if compare_samples:
            cx, cy = extract_channel(compare_samples, "speed", metric=metric)
            self._speed.set_series("compare", cx, cy, theme.OVERSTEER)

        xs_p, ys_p = extract_channel(samples, "power_hp")
        xs_r, ys_r = extract_channel(samples, "rpm")
        self._power_rpm.set_series("hp", xs_p, ys_p, theme.THROTTLE, axis="primary")
        self._power_rpm.set_series("rpm", xs_r, ys_r, theme.ACCENT, axis="secondary")
        markers = [
            GraphMarker(t, f"G{gear}", theme.SHIFT_WARN)
            for t, gear in extract_shift_markers(samples)
        ]
        self._power_rpm.set_markers(markers)

        xs_g, ys_long = extract_channel(samples, "g_long")
        _, ys_lat = extract_channel(samples, "g_lat")
        _, ys_total = extract_channel(samples, "g_total")
        self._gforce.set_series("long", xs_g, ys_long, theme.ACCENT)
        self._gforce.set_series("lat", xs_g, ys_lat, theme.OVERSTEER)
        self._gforce.set_series("total", xs_g, ys_total, theme.TEXT)

        xs_t, ys_fl = extract_channel(samples, "tire_fl", metric=metric)
        _, ys_fr = extract_channel(samples, "tire_fr", metric=metric)
        _, ys_rl = extract_channel(samples, "tire_rl", metric=metric)
        _, ys_rr = extract_channel(samples, "tire_rr", metric=metric)
        self._tyres.set_series("FL", xs_t, ys_fl, theme.TIRE_COLORS["optimal"])
        self._tyres.set_series("FR", xs_t, ys_fr, theme.TIRE_COLORS["warming"])
        self._tyres.set_series("RL", xs_t, ys_rl, theme.TIRE_COLORS["hot"])
        self._tyres.set_series("RR", xs_t, ys_rr, theme.TIRE_COLORS["cold"])

        xs_d, ys_delta = extract_channel(samples, "delta")
        _, ys_bal = extract_channel(samples, "balance")
        self._delta_balance.set_series("delta", xs_d, ys_delta, theme.DELTA_FASTER, axis="primary")
        self._delta_balance.set_series("balance", xs_d, ys_bal, theme.UNDERSTEER, axis="secondary")

        self._update_slider()
        self._apply_view_range()

    def _all_graphs_follow(self, enabled: bool) -> None:
        for graph in self._graphs:
            graph.set_follow_live(enabled, window_seconds=self._window_seconds)

    def _on_follow_toggled(self, checked: bool) -> None:
        self._follow_live = checked
        self._slider.setEnabled(not checked)
        self._all_graphs_follow(checked)
        if checked:
            self._apply_view_range()
        else:
            self._on_slider_changed(self._slider.value())

    def _on_window_changed(self, _index: int) -> None:
        value = self._window_combo.currentData()
        if value:
            self._window_seconds = float(value)
            for graph in self._graphs:
                graph.set_window_seconds(self._window_seconds)
            self._update_slider()
            self._apply_view_range()

    def _update_slider(self) -> None:
        max_start = max(0.0, self._elapsed - self._window_seconds)
        scale = 1000
        max_val = int(max_start * scale)
        self._slider_busy = True
        self._slider.setMaximum(max(max_val, 1))
        if self._follow_live:
            self._slider.setValue(max_val)
        self._slider_busy = False
        end = min(self._elapsed, self._slider.value() / scale + self._window_seconds)
        self._time_label.setText(f"{self._slider.value() / scale:.1f} – {end:.1f} s")

    def _on_slider_changed(self, value: int) -> None:
        if self._slider_busy or self._follow_live:
            return
        start = value / 1000.0
        end = start + self._window_seconds
        self._time_label.setText(f"{start:.1f} – {end:.1f} s")
        for graph in self._graphs:
            graph.set_x_range(start, end)

    def _apply_view_range(self) -> None:
        if self._follow_live:
            self._all_graphs_follow(True)
            self._update_slider()
