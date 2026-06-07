"""Lab application bootstrap."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from ..config import AppConfig
from .window import LabWindow


class LabApplication:
    def __init__(self, config: AppConfig | None = None) -> None:
        self._config = config or AppConfig()
        self._qt = QApplication.instance() or QApplication([])
        self._window = LabWindow(self._config)

    def run(self) -> int:
        self._window.show()
        return self._qt.exec()
