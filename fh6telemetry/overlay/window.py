"""The overlay window: a frameless, translucent, always-on-top HUD.

Responsibilities:

* compose the enabled panels into a compact grid;
* stay on top of the game without stealing focus;
* toggle Windows click-through (input pass-through) so the overlay does not
  block the game while still being draggable when you want to reposition it;
* expose a system-tray menu for the handful of runtime controls.

The window is intentionally passive: the application pushes new HUD state via
:meth:`apply_state`; the window never talks to the network or analytics layers.
"""

from __future__ import annotations

import sys
from collections.abc import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QGridLayout,
    QMenu,
    QSystemTrayIcon,
    QWidget,
)

from ..config import AppConfig
from ..models import HudState
from . import widgets

# (panel key, widget class, grid row, col, rowspan, colspan)
_LAYOUT = [
    ("core", widgets.CorePanel, 0, 0, 1, 2),
    ("gforce", widgets.GForcePanel, 0, 2, 1, 1),
    ("inputs", widgets.InputsPanel, 1, 0, 1, 1),
    ("power", widgets.PowerPanel, 1, 1, 1, 1),
    ("tires", widgets.TiresPanel, 1, 2, 1, 1),
    ("laps", widgets.LapsPanel, 2, 0, 1, 1),
    ("performance", widgets.PerformancePanel, 2, 1, 1, 2),
    ("handling", widgets.HandlingPanel, 3, 0, 1, 3),
]


class OverlayWindow(QWidget):
    def __init__(
        self,
        config: AppConfig,
        on_reset_session: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        super().__init__()
        self._config = config
        self._on_reset_session = on_reset_session
        self._on_quit = on_quit
        self._state = HudState()
        self._blink = False
        self._drag_offset = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowTitle("FH6Telemetry")
        self.setWindowOpacity(config.opacity)

        self._panels: dict[str, widgets.BasePanel] = {}
        self._build_layout()

        self.move(config.window_x, config.window_y)

        # Blink timer drives the shift-light flash and keeps panels live even
        # when telemetry momentarily stops arriving.
        self._timer = QTimer(self)
        self._timer.setInterval(120)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start()

        self._tray = self._build_tray()

    # -- composition ------------------------------------------------------------
    def _build_layout(self) -> None:
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(widgets.SPACING)
        for key, cls, row, col, rspan, cspan in _LAYOUT:
            if not self._config.panels.get(key, True):
                continue
            panel = cls()
            self._panels[key] = panel
            grid.addWidget(panel, row, col, rspan, cspan, Qt.AlignmentFlag.AlignTop)
        self.adjustSize()

    def _build_tray(self) -> QSystemTrayIcon:
        tray = QSystemTrayIcon(self._make_icon(), self)
        tray.setToolTip("FH6Telemetry")
        menu = QMenu()

        self._action_interactive = QAction("Interactive (click-through off)", self)
        self._action_interactive.setCheckable(True)
        self._action_interactive.setChecked(not self._config.click_through)
        self._action_interactive.toggled.connect(self._on_toggle_interactive)
        menu.addAction(self._action_interactive)

        self._action_lock = QAction("Lock position", self)
        self._action_lock.setCheckable(True)
        self._action_lock.setChecked(self._config.locked)
        self._action_lock.toggled.connect(self._on_toggle_lock)
        menu.addAction(self._action_lock)

        self._action_metric = QAction("Metric units", self)
        self._action_metric.setCheckable(True)
        self._action_metric.setChecked(self._config.use_metric)
        self._action_metric.toggled.connect(self._on_toggle_metric)
        menu.addAction(self._action_metric)

        menu.addSeparator()
        reset = QAction("Reset session", self)
        reset.triggered.connect(lambda: self._on_reset_session())
        menu.addAction(reset)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(lambda: self._on_quit())
        menu.addAction(quit_action)

        tray.setContextMenu(menu)
        tray.show()
        return tray

    @staticmethod
    def _make_icon() -> QIcon:
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(0, 200, 255))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(3, 3, 26, 26, 6, 6)
        painter.setPen(QColor(10, 12, 16))
        from PySide6.QtGui import QFont

        painter.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "F6")
        painter.end()
        return QIcon(pixmap)

    # -- state feed -------------------------------------------------------------
    def apply_state(self, state: HudState) -> None:
        self._state = state
        self._refresh()

    def _on_tick(self) -> None:
        if self._state.should_shift:
            self._blink = not self._blink
        else:
            self._blink = False
        self._refresh()

    def _refresh(self) -> None:
        metric = self._config.use_metric
        for panel in self._panels.values():
            panel.set_state(self._state, metric, self._blink)

    # -- runtime controls -------------------------------------------------------
    def show_overlay(self) -> None:
        self.show()
        self._apply_click_through(self._config.click_through)

    def _on_toggle_interactive(self, interactive: bool) -> None:
        self._config.click_through = not interactive
        self._apply_click_through(self._config.click_through)

    def _on_toggle_lock(self, locked: bool) -> None:
        self._config.locked = locked

    def _on_toggle_metric(self, metric: bool) -> None:
        self._config.use_metric = metric
        self._refresh()

    def _apply_click_through(self, enabled: bool) -> None:
        """Toggle OS-level input pass-through (Windows only)."""
        if sys.platform != "win32":
            return
        import ctypes

        gwl_exstyle = -20
        ws_ex_layered = 0x00080000
        ws_ex_transparent = 0x00000020
        hwnd = int(self.winId())
        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(hwnd, gwl_exstyle)
        if enabled:
            style |= ws_ex_layered | ws_ex_transparent
        else:
            style &= ~ws_ex_transparent
        user32.SetWindowLongW(hwnd, gwl_exstyle, style)

    # -- dragging (only possible in interactive mode) --------------------------
    def mousePressEvent(self, event) -> None:
        if self._config.locked:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and not self._config.locked:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None
        self._config.window_x = self.x()
        self._config.window_y = self.y()

    def closeEvent(self, event) -> None:
        self._config.window_x = self.x()
        self._config.window_y = self.y()
        self._config.save()
        self._tray.hide()
        super().closeEvent(event)
