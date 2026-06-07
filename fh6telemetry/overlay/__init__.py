"""PySide6 overlay layer: a transparent, always-on-top in-game HUD.

:class:`~fh6telemetry.overlay.window.OverlayWindow` composes the individual
panel widgets defined in :mod:`fh6telemetry.overlay.widgets` and exposes a
single :meth:`apply_state` entry point that the application calls with each new
:class:`~fh6telemetry.models.HudState`.
"""

from __future__ import annotations

from .window import OverlayWindow

__all__ = ["OverlayWindow"]
