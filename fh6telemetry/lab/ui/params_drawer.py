"""Scenario parameter editor for the Lab sidebar."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QPushButton,
)

from ..scenarios.config import VehicleConfig
from ..scenarios.engine import ScenarioEngine


class ParamsDrawerWidget(QGroupBox):
    def __init__(
        self,
        engine: ScenarioEngine,
        on_apply: Callable[[], None],
        parent=None,
    ) -> None:
        super().__init__("Scenario parameters", parent)
        self._engine = engine
        self._on_apply = on_apply

        form = QFormLayout(self)
        self._redline = QDoubleSpinBox()
        self._redline.setRange(4000.0, 10000.0)
        self._redline.setSingleStep(100.0)
        self._redline.setSuffix(" rpm")

        self._track = QDoubleSpinBox()
        self._track.setRange(500.0, 20000.0)
        self._track.setSingleStep(100.0)
        self._track.setSuffix(" m")

        self._power = QDoubleSpinBox()
        self._power.setRange(0.5, 2.0)
        self._power.setSingleStep(0.05)
        self._power.setSuffix(" ×")

        form.addRow("Redline", self._redline)
        form.addRow("Track length", self._track)
        form.addRow("Power scale", self._power)

        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._apply)
        form.addRow(apply_btn)

    def sync_from_scenario(self) -> None:
        scenario = self._engine.current()
        if scenario is None:
            return
        config = scenario.get_vehicle_config()
        self._redline.setValue(config.redline_rpm)
        self._track.setValue(config.track_length_m)
        self._track.setEnabled(scenario.supports_laps())
        self._power.setValue(config.power_scale)

    def _apply(self) -> None:
        scenario = self._engine.current()
        if scenario is None:
            return
        config = VehicleConfig(
            redline_rpm=self._redline.value(),
            track_length_m=self._track.value(),
            power_scale=self._power.value(),
        )
        scenario.set_vehicle_config(config)
        self._on_apply()
