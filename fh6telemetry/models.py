"""Immutable data structures shared across the application.

Two distinct models are used:

* :class:`TelemetryFrame` is the raw, decoded representation of a single
  Forza "Data Out" UDP datagram. Field names follow the official Forza
  documentation (converted to ``snake_case``) so the parser stays auditable.
* :class:`HudState` is the derived, display-ready snapshot produced by the
  analytics engine and consumed by the overlay. Keeping it separate means the
  rendering layer never needs to know how a value was calculated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

# Wheel ordering used by Forza for every 4-element telemetry array.
FRONT_LEFT = 0
FRONT_RIGHT = 1
REAR_LEFT = 2
REAR_RIGHT = 3


class Drivetrain(IntEnum):
    """Drivetrain layout reported in the sled portion of the packet."""

    FWD = 0
    RWD = 1
    AWD = 2

    @classmethod
    def label(cls, value: int) -> str:
        try:
            return cls(value).name
        except ValueError:
            return "N/A"


@dataclass(slots=True)
class TelemetryFrame:
    """Decoded telemetry for a single UDP packet.

    Every field defaults to ``0`` so a sled-only packet (which lacks the dash
    extension) still yields a fully-formed object. ``has_dash`` records whether
    the dash fields are meaningful for the current frame.
    """

    # --- Sled: session / engine ------------------------------------------------
    is_race_on: int = 0
    timestamp_ms: int = 0
    engine_max_rpm: float = 0.0
    engine_idle_rpm: float = 0.0
    current_engine_rpm: float = 0.0

    # --- Sled: motion ----------------------------------------------------------
    accel_x: float = 0.0
    accel_y: float = 0.0
    accel_z: float = 0.0
    vel_x: float = 0.0
    vel_y: float = 0.0
    vel_z: float = 0.0
    ang_vel_x: float = 0.0
    ang_vel_y: float = 0.0
    ang_vel_z: float = 0.0
    yaw: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0

    # --- Sled: per-wheel arrays (FL, FR, RL, RR) ------------------------------
    suspension_travel_norm: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    tire_slip_ratio: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    wheel_rotation_speed: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    wheel_on_rumble_strip: tuple[int, int, int, int] = (0, 0, 0, 0)
    wheel_in_puddle_depth: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    surface_rumble: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    tire_slip_angle: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    tire_combined_slip: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    suspension_travel_m: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)

    # --- Sled: car identity ----------------------------------------------------
    car_ordinal: int = 0
    car_class: int = 0
    car_performance_index: int = 0
    drivetrain_type: int = 0
    num_cylinders: int = 0

    # --- Horizon extension (FH4/FH5 only, mostly undocumented) -----------------
    car_category: int = 0

    # --- Dash: position / drivetrain ------------------------------------------
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    speed: float = 0.0  # metres / second
    power: float = 0.0  # watts
    torque: float = 0.0  # newton-metres
    tire_temp: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)  # Fahrenheit
    boost: float = 0.0  # PSI
    fuel: float = 0.0  # 0..1 fraction of tank
    distance_traveled: float = 0.0  # metres

    # --- Dash: timing ----------------------------------------------------------
    best_lap: float = 0.0
    last_lap: float = 0.0
    current_lap: float = 0.0
    current_race_time: float = 0.0
    lap_number: int = 0
    race_position: int = 0

    # --- Dash: inputs ----------------------------------------------------------
    accel_input: int = 0  # 0..255
    brake_input: int = 0  # 0..255
    clutch_input: int = 0  # 0..255
    handbrake_input: int = 0  # 0..255
    gear: int = 0
    steer: int = 0  # -127..127
    normalized_driving_line: int = 0
    normalized_ai_brake_diff: int = 0

    # --- Motorsport (2023) extension ------------------------------------------
    tire_wear: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    track_ordinal: int = 0

    # --- Decoder metadata ------------------------------------------------------
    packet_format: str = "unknown"
    has_dash: bool = False

    @property
    def is_active(self) -> bool:
        """True when the game reports an in-progress, un-paused race/drive."""
        return self.is_race_on != 0

    @property
    def rpm_fraction(self) -> float:
        """Current RPM as a 0..1 fraction of the engine's redline."""
        if self.engine_max_rpm <= 0:
            return 0.0
        return _clamp(self.current_engine_rpm / self.engine_max_rpm, 0.0, 1.0)


@dataclass(frozen=True, slots=True)
class HudState:
    """Display-ready snapshot emitted by the analytics engine.

    Frozen so the GUI thread can safely read a published snapshot without
    locking while the producer builds the next one.
    """

    connected: bool = False
    active: bool = False

    # Core drive metrics
    speed_kph: float = 0.0
    speed_mph: float = 0.0
    rpm: float = 0.0
    max_rpm: float = 0.0
    idle_rpm: float = 0.0
    rpm_fraction: float = 0.0
    gear: int = 0
    power_hp: float = 0.0
    power_kw: float = 0.0
    torque_nm: float = 0.0
    boost_psi: float = 0.0
    fuel_fraction: float = 0.0
    drivetrain: str = "N/A"

    # Inputs (0..1)
    throttle: float = 0.0
    brake: float = 0.0
    clutch: float = 0.0
    handbrake: float = 0.0
    steer: float = 0.0  # -1..1

    # Shift advisor
    shift_light: float = 0.0  # 0..1 fill level of the shift indicator
    should_shift: bool = False
    optimal_shift_rpm: float = 0.0

    # G-forces (units of g)
    g_long: float = 0.0  # +accel / -braking
    g_lat: float = 0.0  # +right / -left
    g_total: float = 0.0
    g_peak: float = 0.0

    # Tyres
    tire_temp_c: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    tire_slip: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    tire_status: tuple[str, str, str, str] = ("cold", "cold", "cold", "cold")

    # Handling balance: negative=understeer, positive=oversteer (-1..1)
    balance: float = 0.0
    balance_label: str = "neutral"

    # Lap timing (seconds)
    current_lap: float = 0.0
    last_lap: float = 0.0
    best_lap: float = 0.0
    lap_number: int = 0
    race_position: int = 0
    delta: float = 0.0  # vs best lap, negative = faster
    delta_valid: bool = False

    # Performance / session records
    top_speed_kph: float = 0.0
    max_power_hp: float = 0.0
    accel_runs: tuple[tuple[str, float], ...] = field(default_factory=tuple)
    active_run_label: str = ""

    distance_km: float = 0.0


@dataclass(frozen=True, slots=True)
class TimeSeriesSample:
    """One recorded instant for Lab graphs and session export.

    ``t`` is seconds elapsed since the current session started (monotonic).
    """

    t: float
    frame: TelemetryFrame
    hud: HudState


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
