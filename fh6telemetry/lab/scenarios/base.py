"""Scenario protocol for synthetic telemetry generation."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ...models import TelemetryFrame
from .config import VehicleConfig


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

    def supports_laps(self) -> bool:
        return False

    def get_vehicle_config(self) -> VehicleConfig:
        return VehicleConfig()

    def set_vehicle_config(self, config: VehicleConfig) -> None:
        pass
