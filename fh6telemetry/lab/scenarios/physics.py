"""Shared vehicle constants and helpers for scenario physics."""

from __future__ import annotations

# Typical sportscar parameters used across scenarios.
GEAR_RATIOS = [3.2, 2.1, 1.5, 1.15, 0.92, 0.78]
FINAL_DRIVE = 3.7
WHEEL_CIRCUMFERENCE_M = 2.0
REDLINE_RPM = 7200.0
IDLE_RPM = 900.0
MAX_POWER_W = 360_000.0  # ~480 hp
VEHICLE_MASS_KG = 1400.0
DRAG_COEFF = 0.5 * 0.6  # folded into one constant for simplicity


def rpm_for_speed(speed_ms: float, gear: int) -> float:
    if gear < 1:
        gear = 1
    ratio = GEAR_RATIOS[gear - 1] * FINAL_DRIVE
    wheel_rps = speed_ms / WHEEL_CIRCUMFERENCE_M
    rpm = wheel_rps * ratio * 60.0
    return min(REDLINE_RPM, max(IDLE_RPM, rpm))


def power_from_throttle(throttle: float, rpm: float) -> float:
    frac = rpm / REDLINE_RPM
    return max(0.0, throttle * MAX_POWER_W * frac * (1.2 - frac))


def torque_from_power(power_w: float, rpm: float) -> float:
    import math

    return power_w / max(1.0, rpm * 2.0 * math.pi / 60.0)


def longitudinal_accel(
    speed_ms: float,
    throttle: float,
    brake: float,
    rpm: float,
) -> float:
    """Return acceleration in m/s² from a simple force balance."""
    engine_force = throttle * 9000.0 * (1.0 - rpm / (REDLINE_RPM * 1.2))
    drag = DRAG_COEFF * speed_ms * speed_ms
    brake_force = brake * 12000.0
    return (engine_force - drag - brake_force) / VEHICLE_MASS_KG
