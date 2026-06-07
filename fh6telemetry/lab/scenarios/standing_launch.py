"""Standing-start launch scenario: full throttle, straight line, auto shifts."""

from __future__ import annotations

from ...models import TelemetryFrame
from . import physics as p
from .base import Scenario


class StandingLaunchScenario(Scenario):
    """Accelerate from rest with wide-open throttle to exercise accel analytics."""

    def __init__(self) -> None:
        self._t = 0.0
        self._speed = 0.0
        self._gear = 1
        self._distance = 0.0

    @property
    def id(self) -> str:
        return "standing_launch"

    @property
    def label(self) -> str:
        return "Standing launch"

    def reset(self) -> None:
        self._t = 0.0
        self._speed = 0.0
        self._gear = 1
        self._distance = 0.0

    def step(self, dt: float) -> TelemetryFrame:
        self._t += dt
        throttle = 1.0
        brake = 0.0
        steer = 0.0

        rpm = p.rpm_for_speed(self._speed, self._gear)
        accel = p.longitudinal_accel(self._speed, throttle, brake, rpm)
        self._speed = max(0.0, self._speed + accel * dt)
        self._distance += self._speed * dt
        self._update_gear(rpm)

        rpm = p.rpm_for_speed(self._speed, self._gear)
        power = p.power_from_throttle(throttle, rpm)
        torque = p.torque_from_power(power, rpm)
        long_g = accel / 9.80665
        tire_base_f = 70.0 + self._speed * 0.5

        return TelemetryFrame(
            is_race_on=1,
            timestamp_ms=int(self._t * 1000) & 0xFFFFFFFF,
            engine_max_rpm=p.REDLINE_RPM,
            engine_idle_rpm=p.IDLE_RPM,
            current_engine_rpm=rpm,
            accel_x=0.0,
            accel_y=0.0,
            accel_z=long_g * 9.80665,
            vel_z=self._speed,
            speed=self._speed,
            power=power,
            torque=torque,
            tire_temp=(
                tire_base_f + 6.0,
                tire_base_f + 8.0,
                tire_base_f + 4.0,
                tire_base_f + 5.0,
            ),
            boost=throttle * 12.0,
            fuel=max(0.0, 1.0 - self._distance / 80000.0),
            distance_traveled=self._distance,
            current_lap=self._t,
            current_race_time=self._t,
            lap_number=1,
            race_position=1,
            accel_input=255,
            brake_input=0,
            clutch_input=0,
            handbrake_input=0,
            gear=self._gear,
            steer=0,
            drivetrain_type=1,
            num_cylinders=8,
            car_ordinal=2742,
            car_class=5,
            car_performance_index=801,
            packet_format="horizon_dash",
            has_dash=True,
        )

    def _update_gear(self, rpm: float) -> None:
        if rpm > p.REDLINE_RPM * 0.95 and self._gear < len(p.GEAR_RATIOS):
            self._gear += 1
        elif rpm < p.IDLE_RPM * 1.6 and self._gear > 1:
            self._gear -= 1
