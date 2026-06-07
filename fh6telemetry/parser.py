"""Decoder for Forza "Data Out" UDP datagrams.

Forza ships several wire formats that share a common 232-byte *Sled* header and
differ in how (and whether) the *Car Dash* extension is appended. Sizes:

================  ======  ============================================
Packet size       Game    Layout
================  ======  ============================================
232 bytes         All     Sled only (motion data)
311 bytes         FM7     Sled + Car Dash (dash starts at offset 232)
324 bytes         FH4/5   Sled + 12-byte Horizon gap + Car Dash + pad
331 bytes         FM 2023 Sled + Car Dash + tyre-wear/track extras
================  ======  ============================================

Forza Horizon 6 is expected to reuse the Horizon (324-byte) layout, so that is
the default target, but every documented size is decoded for robustness. All
values are little-endian.
"""

from __future__ import annotations

import struct
from typing import Final

from .models import TelemetryFrame

# --- Field tables ------------------------------------------------------------
# Each entry is (attribute_or_group, struct_code). Grouped per-wheel arrays are
# marked with a trailing index; we assemble them into 4-tuples after unpacking.

_SLED_FIELDS: Final = [
    ("is_race_on", "i"),
    ("timestamp_ms", "I"),
    ("engine_max_rpm", "f"),
    ("engine_idle_rpm", "f"),
    ("current_engine_rpm", "f"),
    ("accel_x", "f"),
    ("accel_y", "f"),
    ("accel_z", "f"),
    ("vel_x", "f"),
    ("vel_y", "f"),
    ("vel_z", "f"),
    ("ang_vel_x", "f"),
    ("ang_vel_y", "f"),
    ("ang_vel_z", "f"),
    ("yaw", "f"),
    ("pitch", "f"),
    ("roll", "f"),
    ("suspension_travel_norm", "f", 4),
    ("tire_slip_ratio", "f", 4),
    ("wheel_rotation_speed", "f", 4),
    ("wheel_on_rumble_strip", "i", 4),
    ("wheel_in_puddle_depth", "f", 4),
    ("surface_rumble", "f", 4),
    ("tire_slip_angle", "f", 4),
    ("tire_combined_slip", "f", 4),
    ("suspension_travel_m", "f", 4),
    ("car_ordinal", "i"),
    ("car_class", "i"),
    ("car_performance_index", "i"),
    ("drivetrain_type", "i"),
    ("num_cylinders", "i"),
]

_DASH_FIELDS: Final = [
    ("position_x", "f"),
    ("position_y", "f"),
    ("position_z", "f"),
    ("speed", "f"),
    ("power", "f"),
    ("torque", "f"),
    ("tire_temp", "f", 4),
    ("boost", "f"),
    ("fuel", "f"),
    ("distance_traveled", "f"),
    ("best_lap", "f"),
    ("last_lap", "f"),
    ("current_lap", "f"),
    ("current_race_time", "f"),
    ("lap_number", "H"),
    ("race_position", "B"),
    ("accel_input", "B"),
    ("brake_input", "B"),
    ("clutch_input", "B"),
    ("handbrake_input", "B"),
    ("gear", "B"),
    ("steer", "b"),
    ("normalized_driving_line", "b"),
    ("normalized_ai_brake_diff", "b"),
]

_FM_EXTRA_FIELDS: Final = [
    ("tire_wear", "f", 4),
    ("track_ordinal", "i"),
]

SLED_SIZE: Final = 232


def _build_struct(fields: list) -> tuple[struct.Struct, list]:
    """Compile a little-endian Struct and a flat name plan for a field table."""
    codes = ["<"]
    plan: list[tuple[str, int]] = []  # (name, repeat) where repeat==1 is scalar
    for entry in fields:
        name, code = entry[0], entry[1]
        repeat = entry[2] if len(entry) > 2 else 1
        codes.append(code * repeat)
        plan.append((name, repeat))
    return struct.Struct("".join(codes)), plan


_SLED_STRUCT, _SLED_PLAN = _build_struct(_SLED_FIELDS)
_DASH_STRUCT, _DASH_PLAN = _build_struct(_DASH_FIELDS)
_FM_EXTRA_STRUCT, _FM_EXTRA_PLAN = _build_struct(_FM_EXTRA_FIELDS)

# packet length -> (format name, dash byte offset or None, fm-extras offset or None)
_LAYOUTS: Final = {
    232: ("sled", None, None),
    311: ("fm7_dash", 232, None),
    324: ("horizon_dash", 244, None),
    331: ("fm2023_dash", 232, 311),
}


def _assign(target: dict, plan: list, values: tuple) -> None:
    """Spread a flat tuple of unpacked values across scalars and 4-tuples."""
    index = 0
    for name, repeat in plan:
        if repeat == 1:
            target[name] = values[index]
            index += 1
        else:
            target[name] = tuple(values[index : index + repeat])
            index += repeat


def detect_format(size: int) -> str:
    """Return the human-readable layout name for a datagram size."""
    layout = _LAYOUTS.get(size)
    return layout[0] if layout else "unknown"


def parse(data: bytes) -> TelemetryFrame | None:
    """Decode a datagram into a :class:`TelemetryFrame`.

    Returns ``None`` for datagrams too small to contain even a sled header so
    callers can simply drop malformed packets.
    """
    if len(data) < SLED_SIZE:
        return None

    layout = _LAYOUTS.get(len(data))
    if layout is None:
        # Unknown size: still decode the sled, and opportunistically decode a
        # dash extension if there's plausibly room for one (Horizon offset).
        fmt_name = "unknown"
        dash_offset = 244 if len(data) >= 244 + _DASH_STRUCT.size else None
        fm_offset = None
    else:
        fmt_name, dash_offset, fm_offset = layout

    fields: dict = {"packet_format": fmt_name}
    _assign(fields, _SLED_PLAN, _SLED_STRUCT.unpack_from(data, 0))

    if dash_offset is not None and len(data) >= dash_offset + _DASH_STRUCT.size:
        # The Horizon layout precedes the dash with a 12-byte block whose first
        # int is the (community-decoded) car category.
        if dash_offset >= SLED_SIZE + 4:
            (fields["car_category"],) = struct.unpack_from("<i", data, SLED_SIZE)
        _assign(fields, _DASH_PLAN, _DASH_STRUCT.unpack_from(data, dash_offset))
        fields["has_dash"] = True

    if fm_offset is not None and len(data) >= fm_offset + _FM_EXTRA_STRUCT.size:
        _assign(fields, _FM_EXTRA_PLAN, _FM_EXTRA_STRUCT.unpack_from(data, fm_offset))

    return TelemetryFrame(**fields)


def encode(frame: TelemetryFrame, *, size: int = 324) -> bytes:
    """Serialise a frame back into a datagram (used by the test simulator).

    Only the sizes in :data:`_LAYOUTS` are supported; defaults to the Horizon
    324-byte layout that Forza Horizon uses.
    """
    layout = _LAYOUTS.get(size)
    if layout is None:
        raise ValueError(f"unsupported packet size: {size}")
    _, dash_offset, fm_offset = layout

    buffer = bytearray(size)

    sled_values: list = []
    for name, repeat in _SLED_PLAN:
        value = getattr(frame, name)
        sled_values.extend(value if repeat > 1 else [value])
    _SLED_STRUCT.pack_into(buffer, 0, *sled_values)

    if dash_offset is not None:
        if dash_offset >= SLED_SIZE + 4:
            struct.pack_into("<i", buffer, SLED_SIZE, frame.car_category)
        dash_values: list = []
        for name, repeat in _DASH_PLAN:
            value = getattr(frame, name)
            dash_values.extend(value if repeat > 1 else [value])
        _DASH_STRUCT.pack_into(buffer, dash_offset, *dash_values)

    if fm_offset is not None:
        fm_values: list = []
        for name, repeat in _FM_EXTRA_PLAN:
            value = getattr(frame, name)
            fm_values.extend(value if repeat > 1 else [value])
        _FM_EXTRA_STRUCT.pack_into(buffer, fm_offset, *fm_values)

    return bytes(buffer)
