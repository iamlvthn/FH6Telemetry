"""Embedded overlay HUD panels for the Lab."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QWidget

from ...models import HudState
from ...overlay import widgets


class HudStripWidget(QWidget):
    """Horizontal strip of core overlay panels driven by the latest :class:`HudState`."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(widgets.SPACING)

        self._core = widgets.CorePanel()
        self._inputs = widgets.InputsPanel()
        self._power = widgets.PowerPanel()
        self._laps = widgets.LapsPanel()

        for panel in (self._core, self._inputs, self._power, self._laps):
            layout.addWidget(panel)

        self._panels = (self._core, self._inputs, self._power, self._laps)
        self._metric = True
        self._state = HudState()

    def set_metric(self, metric: bool) -> None:
        self._metric = metric
        self._apply()

    def apply_state(self, state: HudState) -> None:
        self._state = state
        self._apply()

    def _apply(self) -> None:
        for panel in self._panels:
            panel.set_state(self._state, self._metric, blink=False)
