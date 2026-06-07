"""Optional UDP bridge to feed the in-game overlay from the Lab."""

from __future__ import annotations

import socket

from ..models import TelemetryFrame
from ..parser import encode


class UdpBridge:
    """Encodes frames and sends them to a local overlay listener."""

    def __init__(self, host: str = "127.0.0.1", port: int = 5300) -> None:
        self._host = host
        self._port = port
        self._enabled = False
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, value: bool) -> None:
        self._enabled = value

    def send(self, frame: TelemetryFrame) -> None:
        if not self._enabled:
            return
        packet = encode(frame, size=324)
        self._socket.sendto(packet, (self._host, self._port))

    def close(self) -> None:
        try:
            self._socket.close()
        except OSError:
            pass
