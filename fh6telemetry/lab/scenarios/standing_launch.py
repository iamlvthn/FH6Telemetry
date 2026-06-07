"""Standing-start launch scenario: full throttle, straight line, auto shifts."""

from __future__ import annotations

from ...models import TelemetryFrame
from .base import Scenario
from .config import VehicleConfig
from .vehicle import VehicleModel


class StandingLaunchScenario(Scenario):
    """Accelerate from rest with wide-open throttle to exercise accel analytics."""

    def __init__(self) -> None:
        self._vehicle = VehicleModel()

    @property
    def id(self) -> str:
        return "standing_launch"

    @property
    def label(self) -> str:
        return "Standing launch"

    def reset(self) -> None:
        self._vehicle.reset()

    def step(self, dt: float) -> TelemetryFrame:
        return self._vehicle.step(dt, throttle=1.0, brake=0.0, steer=0.0)

    def get_vehicle_config(self) -> VehicleConfig:
        return self._vehicle.config

    def set_vehicle_config(self, config: VehicleConfig) -> None:
        self._vehicle.apply_config(config)
