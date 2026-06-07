"""Integrated vehicle model shared by Lab scenarios."""

from __future__ import annotations

import math

from ...models import TelemetryFrame
from . import physics as p


class VehicleModel:
    """Steps throttle/brake/steer inputs into plausible telemetry frames."""

    def __init__(self, *, track_length_m: float | None = None) -> None:
        self._track_length = track_length_m
        self._t = 0.0
        self._speed = 0.0
        self._gear = 1
        self._distance = 0.0
        self._shift_cooldown = 0.0
        self._lap = 1
        self._lap_start_distance = 0.0
        self._lap_start_time = 0.0
        self._best_lap = 0.0
        self._last_lap = 0.0

    @property
    def speed(self) -> float:
        return self._speed

    def reset(self) -> None:
        self._t = 0.0
        self._speed = 0.0
        self._gear = 1
        self._distance = 0.0
        self._shift_cooldown = 0.0
        self._lap = 1
        self._lap_start_distance = 0.0
        self._lap_start_time = 0.0
        self._best_lap = 0.0
        self._last_lap = 0.0

    def step(self, dt: float, *, throttle: float, brake: float, steer: float) -> TelemetryFrame:
        self._t += dt
        if self._shift_cooldown > 0:
            self._shift_cooldown = max(0.0, self._shift_cooldown - dt)

        throttle = max(0.0, min(1.0, throttle))
        brake = max(0.0, min(1.0, brake))
        steer = max(-1.0, min(1.0, steer))

        rpm = p.rpm_for_speed(self._speed, self._gear)
        accel = p.longitudinal_accel(self._speed, throttle, brake, rpm, self._gear)
        self._speed = max(0.0, self._speed + accel * dt)
        self._distance += self._speed * dt
        self._update_gear()
        self._update_laps()

        rpm = p.rpm_for_speed(self._speed, self._gear)
        torque = p.engine_torque_nm(rpm) * throttle
        power = p.power_from_torque(torque, rpm)
        long_g = accel / 9.80665
        lat_g = steer * min(1.4, self._speed / 30.0)
        slip = abs(steer) * min(1.5, self._speed / 25.0)
        front_slip = steer * 0.12
        rear_slip = steer * 0.09
        tire_base_f = 70.0 + self._speed * 0.55

        return TelemetryFrame(
            is_race_on=1,
            timestamp_ms=int(self._t * 1000) & 0xFFFFFFFF,
            engine_max_rpm=p.REDLINE_RPM,
            engine_idle_rpm=p.IDLE_RPM,
            current_engine_rpm=rpm,
            accel_x=lat_g * 9.80665,
            accel_y=0.0,
            accel_z=long_g * 9.80665,
            vel_z=self._speed,
            speed=self._speed,
            power=power,
            torque=torque,
            tire_slip_ratio=(slip, slip, slip * 0.8, slip * 0.8),
            tire_slip_angle=(front_slip, front_slip, rear_slip, rear_slip),
            tire_combined_slip=(slip, slip, slip * 0.8, slip * 0.8),
            tire_temp=(
                tire_base_f + 8.0,
                tire_base_f + 10.0,
                tire_base_f + 4.0,
                tire_base_f + 6.0,
            ),
            boost=throttle * 12.0,
            fuel=max(0.0, 1.0 - self._distance / 60000.0),
            distance_traveled=self._distance,
            best_lap=self._best_lap,
            last_lap=self._last_lap,
            current_lap=self._t - self._lap_start_time,
            current_race_time=self._t,
            lap_number=self._lap,
            race_position=1,
            accel_input=int(throttle * 255),
            brake_input=int(brake * 255),
            clutch_input=0,
            handbrake_input=0,
            gear=self._gear,
            steer=int(steer * 127),
            drivetrain_type=1,
            num_cylinders=8,
            car_ordinal=2742,
            car_class=5,
            car_performance_index=801,
            packet_format="horizon_dash",
            has_dash=True,
        )

    def _update_gear(self) -> None:
        if self._shift_cooldown > 0:
            return
        rpm = p.rpm_for_speed(self._speed, self._gear)
        shifted = False
        if rpm > p.REDLINE_RPM * p.SHIFT_UP_FRACTION and self._gear < len(p.GEAR_RATIOS):
            self._gear += 1
            shifted = True
        elif rpm < p.IDLE_RPM * p.SHIFT_DOWN_IDLE_MULT and self._gear > 1:
            self._gear -= 1
            shifted = True
        if shifted:
            self._shift_cooldown = p.SHIFT_COOLDOWN_S

    def _update_laps(self) -> None:
        if self._track_length is None:
            return
        if self._distance - self._lap_start_distance >= self._track_length:
            self._last_lap = self._t - self._lap_start_time
            if self._best_lap <= 0 or self._last_lap < self._best_lap:
                self._best_lap = self._last_lap
            self._lap += 1
            self._lap_start_distance = self._distance
            self._lap_start_time = self._t
