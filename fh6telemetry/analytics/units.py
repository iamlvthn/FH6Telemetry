"""Pure unit-conversion helpers shared by the analytics modules."""

from __future__ import annotations

# Conversion constants
_MS_TO_KPH = 3.6
_MS_TO_MPH = 2.236936
_WATTS_TO_HP = 1.0 / 745.699872  # mechanical horsepower
_WATTS_TO_KW = 1.0 / 1000.0
_GRAVITY = 9.80665  # m/s^2


def ms_to_kph(value: float) -> float:
    return value * _MS_TO_KPH


def ms_to_mph(value: float) -> float:
    return value * _MS_TO_MPH


def watts_to_hp(value: float) -> float:
    return value * _WATTS_TO_HP


def watts_to_kw(value: float) -> float:
    return value * _WATTS_TO_KW


def fahrenheit_to_celsius(value: float) -> float:
    return (value - 32.0) * 5.0 / 9.0


def to_g(acceleration_ms2: float) -> float:
    """Convert an acceleration in m/s^2 into multiples of standard gravity."""
    return acceleration_ms2 / _GRAVITY


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
