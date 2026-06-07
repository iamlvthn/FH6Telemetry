"""Tyre analysis: temperature classification and slip magnitude per corner."""

from __future__ import annotations

from dataclasses import dataclass

from ..models import TelemetryFrame
from .units import clamp, fahrenheit_to_celsius

# Operating-window thresholds in Celsius (typical sim race-tyre window).
_COLD_C = 70.0
_OPTIMAL_LOW_C = 80.0
_OPTIMAL_HIGH_C = 105.0
_HOT_C = 120.0

# Combined-slip value above which a tyre is considered to be losing grip.
_SLIP_LIMIT = 1.0


@dataclass(slots=True)
class TireResult:
    temps_c: tuple[float, float, float, float]
    slip: tuple[float, float, float, float]
    status: tuple[str, str, str, str]


def _classify(temp_c: float) -> str:
    if temp_c < _COLD_C:
        return "cold"
    if temp_c < _OPTIMAL_LOW_C:
        return "warming"
    if temp_c <= _OPTIMAL_HIGH_C:
        return "optimal"
    if temp_c <= _HOT_C:
        return "hot"
    return "overheating"


class TireAnalyzer:
    def update(self, frame: TelemetryFrame) -> TireResult:
        temps_c = tuple(fahrenheit_to_celsius(t) for t in frame.tire_temp)
        slip = tuple(clamp(abs(s), 0.0, 2.0) for s in frame.tire_combined_slip)
        status = tuple(_classify(t) for t in temps_c)
        return TireResult(temps_c=temps_c, slip=slip, status=status)  # type: ignore[arg-type]
