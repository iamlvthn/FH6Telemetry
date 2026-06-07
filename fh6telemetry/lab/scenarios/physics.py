"""Shared vehicle constants and torque-curve physics."""

from __future__ import annotations

import math

# Typical sportscar parameters used across scenarios.
GEAR_RATIOS = [3.2, 2.1, 1.5, 1.15, 0.92, 0.78]
FINAL_DRIVE = 3.7
WHEEL_CIRCUMFERENCE_M = 2.0
WHEEL_RADIUS_M = WHEEL_CIRCUMFERENCE_M / (2.0 * math.pi)
REDLINE_RPM = 7200.0
IDLE_RPM = 900.0
VEHICLE_MASS_KG = 1400.0
DRAG_COEFF = 0.5 * 0.6
MAX_BRAKE_FORCE_N = 12000.0
SHIFT_UP_FRACTION = 0.95
SHIFT_DOWN_IDLE_MULT = 1.6
SHIFT_COOLDOWN_S = 0.15

# RPM → peak torque (Nm) lookup; linear interpolation between points.
TORQUE_CURVE_NM: tuple[tuple[float, float], ...] = (
    (1000.0, 220.0),
    (2000.0, 360.0),
    (3000.0, 430.0),
    (4000.0, 455.0),
    (5000.0, 445.0),
    (6000.0, 410.0),
    (6500.0, 370.0),
    (REDLINE_RPM, 310.0),
)


def rpm_for_speed(speed_ms: float, gear: int) -> float:
    if gear < 1:
        gear = 1
    ratio = GEAR_RATIOS[gear - 1] * FINAL_DRIVE
    wheel_rps = speed_ms / WHEEL_CIRCUMFERENCE_M
    rpm = wheel_rps * ratio * 60.0
    return min(REDLINE_RPM, max(IDLE_RPM, rpm))


def engine_torque_nm(rpm: float) -> float:
    """Interpolate peak engine torque at the current RPM."""
    if rpm <= TORQUE_CURVE_NM[0][0]:
        return TORQUE_CURVE_NM[0][1]
    if rpm >= TORQUE_CURVE_NM[-1][0]:
        return TORQUE_CURVE_NM[-1][1]
    for (r0, t0), (r1, t1) in zip(TORQUE_CURVE_NM, TORQUE_CURVE_NM[1:], strict=False):
        if r0 <= rpm <= r1:
            span = r1 - r0
            if span <= 0:
                return t0
            f = (rpm - r0) / span
            return t0 + (t1 - t0) * f
    return TORQUE_CURVE_NM[-1][1]


def power_from_torque(torque_nm: float, rpm: float) -> float:
    return torque_nm * rpm * 2.0 * math.pi / 60.0


def drive_force_n(throttle: float, rpm: float, gear: int) -> float:
    """Wheel thrust from engine torque through the current gear."""
    if gear < 1:
        gear = 1
    ratio = GEAR_RATIOS[gear - 1] * FINAL_DRIVE
    torque = throttle * engine_torque_nm(rpm)
    wheel_torque = torque * ratio
    return wheel_torque / WHEEL_RADIUS_M


def longitudinal_accel(speed_ms: float, throttle: float, brake: float, rpm: float, gear: int) -> float:
    """Return acceleration in m/s² from torque, drag and braking."""
    engine_force = drive_force_n(throttle, rpm, gear)
    drag = DRAG_COEFF * speed_ms * speed_ms
    brake_force = brake * MAX_BRAKE_FORCE_N
    return (engine_force - drag - brake_force) / VEHICLE_MASS_KG
