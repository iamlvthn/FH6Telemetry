"""Analytics layer: turns raw telemetry frames into display-ready HUD state.

The :class:`~fh6telemetry.analytics.engine.AnalyticsEngine` orchestrates a set
of small, single-responsibility analysers (lap timing, shift advice, tyre and
handling analysis, acceleration runs and session records). Each analyser is
independently testable and can be enabled or extended without touching the
others.
"""

from __future__ import annotations

from .engine import AnalyticsEngine

__all__ = ["AnalyticsEngine"]
