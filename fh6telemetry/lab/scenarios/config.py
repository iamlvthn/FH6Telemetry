"""Configurable vehicle parameters for Lab scenarios."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class VehicleConfig:
    redline_rpm: float = 7200.0
    track_length_m: float = 1800.0
    power_scale: float = 1.0
