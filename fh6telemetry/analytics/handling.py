"""Handling balance: derive understeer/oversteer from per-axle slip angles.

Comparing the average front slip angle against the average rear slip angle
gives a robust, intuitive balance signal:

* front slipping more than rear  -> understeer (push)
* rear slipping more than front   -> oversteer (loose)

The raw difference is smoothed and normalised into a -1..1 value so the overlay
can render a steady balance bar instead of a jittery instantaneous reading.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import FRONT_LEFT, FRONT_RIGHT, REAR_LEFT, REAR_RIGHT, TelemetryFrame
from .units import clamp

# Slip-angle difference (radians) that maps to a full-scale reading.
_FULL_SCALE = 0.20
# Exponential smoothing factor (higher = more responsive, noisier).
_SMOOTHING = 0.20
# Below this lateral activity we report "neutral" to avoid noise at a standstill.
_DEADZONE = 0.02


@dataclass(slots=True)
class HandlingResult:
    balance: float = 0.0  # -1 understeer .. +1 oversteer
    label: str = "neutral"


class HandlingAnalyzer:
    def __init__(self) -> None:
        self._balance = 0.0

    def reset(self) -> None:
        self._balance = 0.0

    def update(self, frame: TelemetryFrame) -> HandlingResult:
        front = (
            abs(frame.tire_slip_angle[FRONT_LEFT])
            + abs(frame.tire_slip_angle[FRONT_RIGHT])
        ) / 2.0
        rear = (
            abs(frame.tire_slip_angle[REAR_LEFT])
            + abs(frame.tire_slip_angle[REAR_RIGHT])
        ) / 2.0

        raw = clamp((front - rear) / _FULL_SCALE, -1.0, 1.0)
        # Negative raw means front slips more -> understeer should read negative.
        target = -raw
        self._balance += (target - self._balance) * _SMOOTHING

        if max(front, rear) < _DEADZONE:
            return HandlingResult(balance=0.0, label="neutral")

        label = "neutral"
        if self._balance < -0.15:
            label = "understeer"
        elif self._balance > 0.15:
            label = "oversteer"
        return HandlingResult(balance=self._balance, label=label)
