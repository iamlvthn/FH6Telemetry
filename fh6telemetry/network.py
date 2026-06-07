"""Threaded UDP listener for Forza telemetry.

The socket runs on its own daemon thread and hands every decoded frame to a
callback. Decoding (and downstream analytics) therefore happens off the GUI
thread, leaving the overlay free to render at a steady frame rate.
"""

from __future__ import annotations

import socket
import threading
from collections.abc import Callable

from .models import TelemetryFrame
from .parser import parse

FrameCallback = Callable[[TelemetryFrame], None]

# Forza datagrams top out at 331 bytes; 4 KiB is comfortably larger.
_RECV_BUFFER = 4096
# Periodically wake from recv so the thread can observe the stop flag.
_SOCKET_TIMEOUT_S = 0.5


class UDPTelemetryListener:
    """Receives Forza "Data Out" datagrams and dispatches decoded frames."""

    def __init__(
        self,
        host: str,
        port: int,
        on_frame: FrameCallback,
        on_status: Callable[[bool], None] | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._on_frame = on_frame
        self._on_status = on_status
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._socket: socket.socket | None = None
        self._connected = False

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Bind the socket and begin receiving on a background thread."""
        if self.is_running:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self._host, self._port))
        sock.settimeout(_SOCKET_TIMEOUT_S)
        self._socket = sock
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="fh6-udp-listener", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Signal the thread to exit and wait briefly for it to unwind."""
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=2.0)
        self._thread = None
        if self._socket is not None:
            try:
                self._socket.close()
            finally:
                self._socket = None
        self._set_connected(False)

    def _run(self) -> None:
        assert self._socket is not None
        while not self._stop.is_set():
            try:
                data, _addr = self._socket.recvfrom(_RECV_BUFFER)
            except socket.timeout:
                # No data within the window: treat as "waiting for game".
                self._set_connected(False)
                continue
            except OSError:
                break

            frame = parse(data)
            if frame is None:
                continue
            self._set_connected(True)
            try:
                self._on_frame(frame)
            except Exception:
                # A misbehaving consumer must never kill the receive loop.
                continue

    def _set_connected(self, value: bool) -> None:
        if value == self._connected:
            return
        self._connected = value
        if self._on_status is not None:
            self._on_status(value)
