"""Synthetic Forza telemetry generator for local testing.

Forza Horizon only emits telemetry to a remote IP, so you cannot normally test
a PC overlay using the same machine. This simulator fabricates a believable
drive - accelerating, shifting, cornering and lapping - and streams encoded
324-byte Horizon datagrams to the overlay so the full pipeline can be exercised
without the game.

Usage::

    python -m tools.simulator                # -> 127.0.0.1:5300 at 60 Hz
    python -m tools.simulator --host 1.2.3.4 --port 5300
"""

from __future__ import annotations

import argparse
import math
import socket
import time

from fh6telemetry.models import TelemetryFrame
from fh6telemetry.parser import encode

_GEAR_RATIOS = [3.2, 2.1, 1.5, 1.15, 0.92, 0.78]  # per forward gear
_FINAL_DRIVE = 3.7
_WHEEL_CIRCUMFERENCE = 2.0  # metres
_REDLINE = 7200.0
_IDLE = 900.0
_MAX_POWER_W = 360_000.0  # ~480 hp peak
_TRACK_LENGTH = 1800.0  # metres per lap


class _DriveModel:
    """A tiny longitudinal/lateral model producing plausible telemetry."""

    def __init__(self) -> None:
        self.t = 0.0
        self.speed = 0.0  # m/s
        self.gear = 1
        self.distance = 0.0
        self.lap = 1
        self.lap_start_distance = 0.0
        self.lap_start_time = 0.0
        self.best_lap = 0.0
        self.last_lap = 0.0

    def step(self, dt: float) -> TelemetryFrame:
        self.t += dt

        # Corner phase drives throttle, braking and steering together so the
        # car launches hard, brakes into corners and powers down the straights -
        # exercising shifts, g-forces, slip and acceleration runs.
        corner = math.sin(self.t * 0.45)
        throttle = max(0.0, min(1.0, 0.8 + 0.3 * corner))
        brake = 0.7 if corner < -0.85 else 0.0
        steer = math.sin(self.t * 0.45 + math.pi / 2) * min(1.0, self.speed / 30.0)

        rpm = self._rpm_for_speed()
        # Simple force balance: engine pull vs drag/brake.
        engine_force = throttle * 9000.0 * (1.0 - rpm / (_REDLINE * 1.2))
        drag = 0.5 * self.speed * self.speed * 0.6
        brake_force = brake * 12000.0
        accel = (engine_force - drag - brake_force) / 1400.0
        self.speed = max(0.0, self.speed + accel * dt)

        self._update_gear(rpm)

        self.distance += self.speed * dt
        self._update_laps()

        lat_g = steer * min(1.4, self.speed / 30.0)
        long_g = accel / 9.80665

        rpm = self._rpm_for_speed()
        power = max(0.0, throttle * _MAX_POWER_W * (rpm / _REDLINE) * (1.2 - rpm / _REDLINE))
        torque = power / max(1.0, rpm * 2 * math.pi / 60.0)

        slip = abs(steer) * min(1.5, self.speed / 25.0)
        tire_base = 70.0 + self.speed * 0.6
        front_slip_angle = steer * 0.12
        rear_slip_angle = steer * 0.09

        return TelemetryFrame(
            is_race_on=1,
            timestamp_ms=int(self.t * 1000) & 0xFFFFFFFF,
            engine_max_rpm=_REDLINE,
            engine_idle_rpm=_IDLE,
            current_engine_rpm=rpm,
            accel_x=lat_g * 9.80665,
            accel_y=0.0,
            accel_z=long_g * 9.80665,
            vel_x=0.0,
            vel_y=0.0,
            vel_z=self.speed,
            yaw=0.0,
            pitch=0.0,
            roll=0.0,
            tire_slip_ratio=(slip, slip, slip * 0.8, slip * 0.8),
            tire_slip_angle=(
                front_slip_angle,
                front_slip_angle,
                rear_slip_angle,
                rear_slip_angle,
            ),
            tire_combined_slip=(slip, slip, slip * 0.8, slip * 0.8),
            car_ordinal=2742,
            car_class=5,
            car_performance_index=801,
            drivetrain_type=1,
            num_cylinders=8,
            speed=self.speed,
            power=power,
            torque=torque,
            tire_temp=(
                tire_base + 8,
                tire_base + 10,
                tire_base + 4,
                tire_base + 6,
            ),
            boost=throttle * 12.0,
            fuel=max(0.0, 1.0 - self.distance / 60000.0),
            distance_traveled=self.distance,
            best_lap=self.best_lap,
            last_lap=self.last_lap,
            current_lap=self.t - self.lap_start_time,
            current_race_time=self.t,
            lap_number=self.lap,
            race_position=3,
            accel_input=int(throttle * 255),
            brake_input=int(brake * 255),
            clutch_input=0,
            handbrake_input=0,
            gear=self.gear,
            steer=int(steer * 127),
            normalized_driving_line=0,
            normalized_ai_brake_diff=0,
            packet_format="horizon_dash",
            has_dash=True,
        )

    def _rpm_for_speed(self) -> float:
        ratio = _GEAR_RATIOS[self.gear - 1] * _FINAL_DRIVE
        wheel_rps = self.speed / _WHEEL_CIRCUMFERENCE
        rpm = wheel_rps * ratio * 60.0
        return min(_REDLINE, max(_IDLE, rpm))

    def _update_gear(self, rpm: float) -> None:
        if rpm > _REDLINE * 0.95 and self.gear < len(_GEAR_RATIOS):
            self.gear += 1
        elif rpm < _IDLE * 1.6 and self.gear > 1:
            self.gear -= 1

    def _update_laps(self) -> None:
        if self.distance - self.lap_start_distance >= _TRACK_LENGTH:
            self.last_lap = self.t - self.lap_start_time
            if self.best_lap <= 0 or self.last_lap < self.best_lap:
                self.best_lap = self.last_lap
            self.lap += 1
            self.lap_start_distance = self.distance
            self.lap_start_time = self.t


def main() -> int:
    parser = argparse.ArgumentParser(description="Forza telemetry simulator.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5300)
    parser.add_argument("--rate", type=float, default=60.0, help="Packets per second.")
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    model = _DriveModel()
    dt = 1.0 / args.rate
    print(f"Streaming simulated FH telemetry to {args.host}:{args.port} at {args.rate:g} Hz")
    print("Press Ctrl+C to stop.")
    try:
        while True:
            frame = model.step(dt)
            sock.sendto(encode(frame, size=324), (args.host, args.port))
            time.sleep(dt)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        sock.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
