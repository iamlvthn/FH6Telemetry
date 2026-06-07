"""Fixed-capacity ring buffer of telemetry samples for Lab graphs."""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence

from ...models import HudState, TelemetryFrame, TimeSeriesSample

# Default: 60 seconds at 60 Hz.
DEFAULT_CAPACITY = 3600


class SessionBuffer:
    """Stores the most recent :class:`TimeSeriesSample` values in FIFO order."""

    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        self._capacity = max(1, capacity)
        self._samples: deque[TimeSeriesSample] = deque(maxlen=self._capacity)
        self._elapsed = 0.0

    @property
    def elapsed(self) -> float:
        """Seconds recorded in the current session."""
        return self._elapsed

    @property
    def count(self) -> int:
        return len(self._samples)

    def clear(self) -> None:
        self._samples.clear()
        self._elapsed = 0.0

    def load_samples(self, samples: Sequence[TimeSeriesSample]) -> None:
        """Replace the buffer with a pre-built session (CSV import / replay)."""
        self._samples.clear()
        for sample in samples:
            self._samples.append(sample)
        self._elapsed = samples[-1].t if samples else 0.0

    def append_sample(self, sample: TimeSeriesSample) -> None:
        """Append an existing sample (replay animation)."""
        self._samples.append(sample)
        self._elapsed = sample.t

    def append(self, frame: TelemetryFrame, hud: HudState, *, dt: float) -> TimeSeriesSample:
        """Record a new sample, advancing the session clock by ``dt``."""
        self._elapsed += dt
        sample = TimeSeriesSample(t=self._elapsed, frame=frame, hud=hud)
        self._samples.append(sample)
        return sample

    def samples(self) -> Sequence[TimeSeriesSample]:
        return tuple(self._samples)

    def slice_time(self, start: float, end: float) -> list[TimeSeriesSample]:
        """Return samples whose ``t`` lies in ``[start, end]``."""
        return [s for s in self._samples if start <= s.t <= end]
