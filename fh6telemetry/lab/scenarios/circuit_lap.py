"""Circuit lap scenario: straights, braking zones and corners."""

from __future__ import annotations

import math

from ...models import TelemetryFrame
from .base import Scenario
from .config import VehicleConfig
from .vehicle import VehicleModel

class CircuitLapScenario(Scenario):
    """Repeated laps with throttle/brake/steer phases to exercise lap analytics."""

    def __init__(self) -> None:
        self._vehicle = VehicleModel(enable_laps=True)
        self._t = 0.0

    @property
    def id(self) -> str:
        return "circuit_lap"

    @property
    def label(self) -> str:
        return "Circuit lap"

    def reset(self) -> None:
        self._vehicle.reset()
        self._t = 0.0

    def step(self, dt: float) -> TelemetryFrame:
        self._t += dt
        corner = math.sin(self._t * 0.45)
        throttle = max(0.0, min(1.0, 0.8 + 0.3 * corner))
        brake = 0.7 if corner < -0.85 else 0.0
        steer = math.sin(self._t * 0.45 + math.pi / 2) * min(1.0, self._vehicle.speed / 30.0)
        return self._vehicle.step(dt, throttle=throttle, brake=brake, steer=steer)

    def supports_laps(self) -> bool:
        return True

    def get_vehicle_config(self) -> VehicleConfig:
        return self._vehicle.config

    def set_vehicle_config(self, config: VehicleConfig) -> None:
        self._vehicle.apply_config(config)
