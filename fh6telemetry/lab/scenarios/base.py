"""Scenario protocol for synthetic telemetry generation."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ...models import TelemetryFrame


class Scenario(ABC):
    """Produces a stream of :class:`TelemetryFrame` values when stepped."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Stable machine identifier (e.g. ``standing_launch``)."""

    @property
    @abstractmethod
    def label(self) -> str:
        """Human-readable name for UI pickers."""

    @abstractmethod
    def reset(self) -> None:
        """Return the scenario to its initial state."""

    @abstractmethod
    def step(self, dt: float) -> TelemetryFrame:
        """Advance the simulation by ``dt`` seconds and return the new frame."""
