"""Application wiring.

Connects the three independent layers:

    UDP listener (thread)  ->  analytics engine  ->  Qt overlay (GUI thread)

The listener thread decodes packets and runs analytics, then publishes an
immutable :class:`HudState` to the GUI thread through a queued Qt signal (the
only thread boundary). Session resets are requested via a flag that the
listener thread observes, so the engine's mutable state is never touched from
two threads at once.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QApplication

from .analytics import AnalyticsEngine
from .config import AppConfig
from .models import HudState, TelemetryFrame
from .network import UDPTelemetryListener
from .overlay import OverlayWindow


class _StateBridge(QObject):
    """Marshals HUD snapshots from the listener thread to the GUI thread."""

    state_ready = Signal(object)
    status_changed = Signal(bool)


class Application:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._engine = AnalyticsEngine(config)
        self._reset_requested = threading.Event()

        self._qt = QApplication.instance() or QApplication([])
        self._qt.setQuitOnLastWindowClosed(False)

        self._bridge = _StateBridge()
        self._bridge.state_ready.connect(
            self._on_state, Qt.ConnectionType.QueuedConnection
        )
        self._bridge.status_changed.connect(
            self._on_status, Qt.ConnectionType.QueuedConnection
        )

        self._overlay = OverlayWindow(
            config,
            on_reset_session=self._request_reset,
            on_quit=self.quit,
        )

        self._listener = UDPTelemetryListener(
            host=config.host,
            port=config.port,
            on_frame=self._handle_frame,
            on_status=self._bridge.status_changed.emit,
        )

    # -- listener-thread side ---------------------------------------------------
    def _handle_frame(self, frame: TelemetryFrame) -> None:
        if self._reset_requested.is_set():
            self._reset_requested.clear()
            self._engine.reset_session()
        state = self._engine.process(frame)
        self._bridge.state_ready.emit(state)

    def _request_reset(self) -> None:
        self._reset_requested.set()

    # -- GUI-thread side --------------------------------------------------------
    def _on_state(self, state: HudState) -> None:
        self._overlay.apply_state(state)

    def _on_status(self, connected: bool) -> None:
        if not connected:
            self._overlay.apply_state(HudState(connected=False))

    def run(self) -> int:
        self._overlay.show_overlay()
        self._listener.start()
        try:
            return self._qt.exec()
        finally:
            self._listener.stop()

    def quit(self) -> None:
        self._listener.stop()
        self._config.save()
        self._overlay.close()
        self._qt.quit()
