"""Session statistics panel for the Lab sidebar."""

from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel

from ...models import HudState


class StatsPanelWidget(QGroupBox):
    def __init__(self, parent=None) -> None:
        super().__init__("Session", parent)
        form = QFormLayout(self)
        self._elapsed = QLabel("0.0 s")
        self._distance = QLabel("0.0 km")
        self._top_speed = QLabel("0")
        self._max_power = QLabel("0 hp")
        self._peak_g = QLabel("0.00 g")
        self._best_lap = QLabel("--")
        self._accel = QLabel("—")
        form.addRow("Elapsed", self._elapsed)
        form.addRow("Distance", self._distance)
        form.addRow("Top speed", self._top_speed)
        form.addRow("Peak power", self._max_power)
        form.addRow("Peak g", self._peak_g)
        form.addRow("Best lap", self._best_lap)
        form.addRow("Accel runs", self._accel)

    def update_from(self, state: HudState, *, elapsed: float, metric: bool) -> None:
        unit = "km/h" if metric else "mph"
        top = state.top_speed_kph if metric else state.top_speed_kph * 0.621371
        self._elapsed.setText(f"{elapsed:.1f} s")
        self._distance.setText(f"{state.distance_km:.2f} km")
        self._top_speed.setText(f"{top:.0f} {unit}")
        self._max_power.setText(f"{state.max_power_hp:.0f} hp")
        self._peak_g.setText(f"{state.g_peak:.2f} g")
        self._best_lap.setText(f"{state.best_lap:.3f} s" if state.best_lap > 0 else "--")
        if state.accel_runs:
            text = "  |  ".join(f"{label} {sec:.2f}s" for label, sec in state.accel_runs[:4])
            self._accel.setText(text)
        else:
            self._accel.setText("—")

    def clear(self) -> None:
        self.update_from(HudState(), elapsed=0.0, metric=True)
