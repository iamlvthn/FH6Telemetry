"""Playback controller for loaded CSV sessions."""

from __future__ import annotations

from collections.abc import Sequence

from ..models import TimeSeriesSample


class ReplayPlayer:
    """Steps through pre-loaded samples at real-time cadence."""

    def __init__(self, samples: Sequence[TimeSeriesSample]) -> None:
        self._samples = list(samples)
        self._index = 0

    @property
    def total(self) -> int:
        return len(self._samples)

    @property
    def position(self) -> int:
        return self._index

    @property
    def finished(self) -> bool:
        return self._index >= len(self._samples)

    def reset(self) -> None:
        self._index = 0

    def step(self) -> TimeSeriesSample | None:
        if self.finished:
            return None
        sample = self._samples[self._index]
        self._index += 1
        return sample
