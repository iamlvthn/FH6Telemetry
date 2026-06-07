"""Acceleration runs and session records.

Detects standing-start acceleration runs (0-100 km/h, 0-200 km/h, the 100-200
roll and the standing quarter mile) by watching for a launch from rest, and
keeps running session records for top speed, peak power and peak g-force.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..models import TelemetryFrame
from .units import ms_to_kph, to_g, watts_to_hp

# (threshold m/s, label). 100 km/h = 27.78 m/s, 200 km/h = 55.56 m/s.
_SPEED_TARGETS: tuple[tuple[float, str], ...] = (
    (27.778, "0-100"),
    (55.556, "0-200"),
)
_QUARTER_MILE_M = 402.336
_LAUNCH_SPEED = 1.0  # m/s, run timing starts here
_STOP_SPEED = 0.6  # m/s, below this we re-arm for the next launch


@dataclass(slots=True)
class PerformanceResult:
    top_speed_kph: float = 0.0
    max_power_hp: float = 0.0
    max_g: float = 0.0
    runs: tuple[tuple[str, float], ...] = field(default_factory=tuple)
    active_label: str = ""


class PerformanceTracker:
    def __init__(self) -> None:
        self._top_speed = 0.0
        self._max_power = 0.0
        self._max_g = 0.0
        self._armed = False
        self._running = False
        self._launch_ms = 0
        self._launch_distance = 0.0
        self._results: dict[str, float] = {}
        self._active_label = ""

    def reset(self) -> None:
        self.__init__()

    def update(self, frame: TelemetryFrame, g_total: float) -> PerformanceResult:
        speed = frame.speed
        self._top_speed = max(self._top_speed, ms_to_kph(speed))
        self._max_power = max(self._max_power, watts_to_hp(frame.power))
        self._max_g = max(self._max_g, g_total)

        self._update_runs(frame, speed)

        return PerformanceResult(
            top_speed_kph=self._top_speed,
            max_power_hp=self._max_power,
            max_g=self._max_g,
            runs=self._ordered_results(),
            active_label=self._active_label,
        )

    def _update_runs(self, frame: TelemetryFrame, speed: float) -> None:
        if speed < _STOP_SPEED:
            self._armed = True
            self._running = False
            self._active_label = ""
            return

        # Begin timing the instant we leave the line under throttle.
        if self._armed and not self._running and speed >= _LAUNCH_SPEED:
            if frame.accel_input > 100:
                self._running = True
                self._armed = False
                self._launch_ms = frame.timestamp_ms
                self._launch_distance = frame.distance_traveled
                self._results = {}

        if not self._running:
            return

        elapsed = self._elapsed_s(frame.timestamp_ms)
        self._active_label = self._next_target_label(speed)

        for threshold, label in _SPEED_TARGETS:
            if speed >= threshold and label not in self._results:
                self._results[label] = elapsed

        distance = frame.distance_traveled - self._launch_distance
        if distance >= _QUARTER_MILE_M and "1/4mi" not in self._results:
            self._results["1/4mi"] = elapsed

    def _next_target_label(self, speed: float) -> str:
        for threshold, label in _SPEED_TARGETS:
            if speed < threshold:
                return label
        return "1/4mi" if "1/4mi" not in self._results else ""

    def _elapsed_s(self, timestamp_ms: int) -> float:
        # uint32 millisecond clock; mask handles the rare wrap-around.
        delta = (timestamp_ms - self._launch_ms) & 0xFFFFFFFF
        return delta / 1000.0

    def _ordered_results(self) -> tuple[tuple[str, float], ...]:
        order = [label for _, label in _SPEED_TARGETS] + ["1/4mi"]
        out: list[tuple[str, float]] = []
        for label in order:
            if label in self._results:
                out.append((label, self._results[label]))
        # Derived 100-200 km/h roll time when both splits exist.
        if "0-100" in self._results and "0-200" in self._results:
            out.append(("100-200", self._results["0-200"] - self._results["0-100"]))
        return tuple(out)
