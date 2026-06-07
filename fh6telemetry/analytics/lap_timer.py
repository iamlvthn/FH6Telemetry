"""Lap timing with a distance-based predictive delta.

Forza already reports current/last/best lap times, but not a *live* delta. This
analyser records a (distance-into-lap -> time-into-lap) trace for the best lap
seen so far, then interpolates it against the current lap's distance to produce
a predictive gap, exactly like the on-screen delta bar in racing sims.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field

from ..models import TelemetryFrame


@dataclass(slots=True)
class _LapTrace:
    """Monotonic samples of (lap_distance_m, lap_time_s) for one lap."""

    distances: list[float] = field(default_factory=list)
    times: list[float] = field(default_factory=list)

    def add(self, distance: float, time: float) -> None:
        # Keep distance strictly increasing so bisect stays valid.
        if self.distances and distance <= self.distances[-1]:
            return
        self.distances.append(distance)
        self.times.append(time)

    def time_at(self, distance: float) -> float | None:
        """Linear-interpolated lap time at a given distance into the lap."""
        if len(self.distances) < 2:
            return None
        if distance <= self.distances[0]:
            return self.times[0]
        if distance >= self.distances[-1]:
            return self.times[-1]
        idx = bisect.bisect_left(self.distances, distance)
        d0, d1 = self.distances[idx - 1], self.distances[idx]
        t0, t1 = self.times[idx - 1], self.times[idx]
        span = d1 - d0
        if span <= 0:
            return t0
        ratio = (distance - d0) / span
        return t0 + ratio * (t1 - t0)


@dataclass(slots=True)
class LapResult:
    current_lap: float = 0.0
    last_lap: float = 0.0
    best_lap: float = 0.0
    lap_number: int = 0
    race_position: int = 0
    delta: float = 0.0
    delta_valid: bool = False


class LapTimer:
    """Tracks lap progress and computes a predictive delta to the best lap."""

    def __init__(self) -> None:
        self._best_trace: _LapTrace | None = None
        self._current_trace = _LapTrace()
        self._lap_start_distance: float | None = None
        self._last_lap_number = -1
        self._best_lap_time = 0.0

    def reset(self) -> None:
        self.__init__()

    def update(self, frame: TelemetryFrame) -> LapResult:
        result = LapResult(
            current_lap=frame.current_lap,
            last_lap=frame.last_lap,
            best_lap=frame.best_lap,
            lap_number=frame.lap_number,
            race_position=frame.race_position,
        )

        if not frame.has_dash:
            return result

        # Detect a new lap: either the lap counter advanced or the lap clock
        # reset back toward zero (covers free-roam/rivals restarts).
        new_lap = frame.lap_number != self._last_lap_number
        if self._lap_start_distance is None:
            self._lap_start_distance = frame.distance_traveled

        if new_lap:
            self._finalize_lap(frame)
            self._last_lap_number = frame.lap_number
            self._lap_start_distance = frame.distance_traveled
            self._current_trace = _LapTrace()

        lap_distance = max(0.0, frame.distance_traveled - self._lap_start_distance)
        self._current_trace.add(lap_distance, frame.current_lap)

        if self._best_trace is not None:
            reference = self._best_trace.time_at(lap_distance)
            if reference is not None:
                result.delta = frame.current_lap - reference
                result.delta_valid = True

        return result

    def _finalize_lap(self, frame: TelemetryFrame) -> None:
        """Promote the just-completed lap to "best" when it is the fastest."""
        completed = frame.last_lap
        if completed <= 0:
            return
        if self._best_lap_time <= 0 or completed < self._best_lap_time:
            if len(self._current_trace.distances) >= 2:
                self._best_lap_time = completed
                self._best_trace = self._current_trace
