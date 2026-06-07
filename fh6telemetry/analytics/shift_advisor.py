"""Shift advisor: learns the engine power band and recommends upshifts.

Without access to gear ratios we cannot compute the theoretically perfect shift
point analytically, so we take a robust, data-driven approach: sample engine
power against RPM while driving to learn where peak power occurs. The optimal
upshift RPM sits a little past peak power (where staying in gear would drop you
below the power you'd get after shifting). A configurable shift light fills as
RPM approaches the redline and turns "critical" near it.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import TelemetryFrame
from .units import clamp

# Resolution of the learned power curve (RPM per bucket).
_RPM_BUCKET = 250.0
# Recommend shifting this fraction of the way from peak-power RPM to redline.
_POST_PEAK_FACTOR = 0.55


@dataclass(slots=True)
class ShiftResult:
    light: float = 0.0  # 0..1 indicator fill
    should_shift: bool = False
    optimal_rpm: float = 0.0


class ShiftAdvisor:
    def __init__(self, light_start: float, light_redline: float) -> None:
        self._light_start = light_start
        self._light_redline = light_redline
        # bucket_index -> best observed power (watts) at that RPM
        self._power_curve: dict[int, float] = {}
        self._peak_power_rpm = 0.0
        self._peak_power = 0.0

    def reset(self) -> None:
        self._power_curve.clear()
        self._peak_power_rpm = 0.0
        self._peak_power = 0.0

    def update(self, frame: TelemetryFrame) -> ShiftResult:
        max_rpm = frame.engine_max_rpm
        rpm = frame.current_engine_rpm
        if max_rpm <= 0:
            return ShiftResult()

        self._learn(frame)

        fraction = clamp(rpm / max_rpm, 0.0, 1.0)
        # Map [light_start, redline] onto the 0..1 light fill.
        span = max(1e-6, self._light_redline - self._light_start)
        light = clamp((fraction - self._light_start) / span, 0.0, 1.0)

        optimal = self._optimal_shift_rpm(max_rpm)
        should_shift = frame.gear > 0 and rpm >= optimal > 0

        return ShiftResult(light=light, should_shift=should_shift, optimal_rpm=optimal)

    def _learn(self, frame: TelemetryFrame) -> None:
        # Only learn under power and off the rev limiter to avoid skewed data.
        if frame.accel_input < 200 or frame.power <= 0:
            return
        if frame.current_engine_rpm >= frame.engine_max_rpm * 0.995:
            return
        bucket = int(frame.current_engine_rpm // _RPM_BUCKET)
        if frame.power > self._power_curve.get(bucket, 0.0):
            self._power_curve[bucket] = frame.power
            if frame.power > self._peak_power:
                self._peak_power = frame.power
                self._peak_power_rpm = bucket * _RPM_BUCKET

    def _optimal_shift_rpm(self, max_rpm: float) -> float:
        if self._peak_power_rpm <= 0:
            # Fall back to a sensible default near the redline until we learn.
            return max_rpm * self._light_redline
        target = self._peak_power_rpm + (max_rpm - self._peak_power_rpm) * _POST_PEAK_FACTOR
        return min(target, max_rpm * 0.99)
