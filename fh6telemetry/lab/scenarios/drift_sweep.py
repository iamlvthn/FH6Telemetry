"""Drift sweep scenario: sustained steer with throttle modulation."""

from __future__ import annotations

import math

from ...models import TelemetryFrame
from .base import Scenario
from .config import VehicleConfig
from .vehicle import VehicleModel


class DriftSweepScenario(Scenario):
    """High slip angles and lateral g to exercise handling and tyre analytics."""

    def __init__(self) -> None:
        self._vehicle = VehicleModel()
        self._t = 0.0

    @property
    def id(self) -> str:
        return "drift_sweep"

    @property
    def label(self) -> str:
        return "Drift sweep"

    def reset(self) -> None:
        self._vehicle.reset()
        self._t = 0.0

    def step(self, dt: float) -> TelemetryFrame:
        self._t += dt
        throttle = 0.85 + 0.15 * math.sin(self._t * 1.2)
        steer = math.sin(self._t * 0.9) * 0.95
        brake = 0.35 if math.sin(self._t * 2.0) > 0.85 else 0.0
        return self._vehicle.step(dt, throttle=throttle, brake=brake, steer=steer)

    def get_vehicle_config(self) -> VehicleConfig:
        return self._vehicle.config

    def set_vehicle_config(self, config: VehicleConfig) -> None:
        self._vehicle.apply_config(config)
