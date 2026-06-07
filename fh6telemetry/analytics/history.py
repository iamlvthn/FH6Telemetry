"""Helpers for extracting graph channels from recorded session samples."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from ..models import FRONT_LEFT, FRONT_RIGHT, REAR_LEFT, REAR_RIGHT, TimeSeriesSample

ChannelFn = Callable[[TimeSeriesSample, bool], float]

# ``metric`` selects km/h / °C when True, mph / °F when False.
CHANNELS: dict[str, ChannelFn] = {
    "speed": lambda s, m: s.hud.speed_kph if m else s.hud.speed_mph,
    "rpm": lambda s, _: s.hud.rpm,
    "power_hp": lambda s, _: s.hud.power_hp,
    "torque_nm": lambda s, _: s.hud.torque_nm,
    "throttle": lambda s, _: s.hud.throttle * 100.0,
    "brake": lambda s, _: s.hud.brake * 100.0,
    "g_long": lambda s, _: s.hud.g_long,
    "g_lat": lambda s, _: s.hud.g_lat,
    "g_total": lambda s, _: s.hud.g_total,
    "balance": lambda s, _: s.hud.balance,
    "delta": lambda s, _: s.hud.delta if s.hud.delta_valid else float("nan"),
    "tire_fl": lambda s, m: _tire_temp(s, FRONT_LEFT, m),
    "tire_fr": lambda s, m: _tire_temp(s, FRONT_RIGHT, m),
    "tire_rl": lambda s, m: _tire_temp(s, REAR_LEFT, m),
    "tire_rr": lambda s, m: _tire_temp(s, REAR_RIGHT, m),
}

CHANNEL_LABELS: dict[str, str] = {
    "speed": "Speed",
    "rpm": "RPM",
    "power_hp": "Power (hp)",
    "torque_nm": "Torque (Nm)",
    "throttle": "Throttle (%)",
    "brake": "Brake (%)",
    "g_long": "G long",
    "g_lat": "G lat",
    "g_total": "G total",
    "balance": "Balance",
    "delta": "Delta (s)",
    "tire_fl": "Tyre FL",
    "tire_fr": "Tyre FR",
    "tire_rl": "Tyre RL",
    "tire_rr": "Tyre RR",
}


def _tire_temp(sample: TimeSeriesSample, corner: int, metric: bool) -> float:
    temp_c = sample.hud.tire_temp_c[corner]
    if metric:
        return temp_c
    return temp_c * 9.0 / 5.0 + 32.0


def extract_channel(
    samples: Sequence[TimeSeriesSample],
    channel: str,
    *,
    metric: bool = True,
) -> tuple[list[float], list[float]]:
    """Return parallel ``(times, values)`` lists for a named channel."""
    fn = CHANNELS.get(channel)
    if fn is None:
        raise KeyError(f"unknown channel: {channel}")
    xs: list[float] = []
    ys: list[float] = []
    for sample in samples:
        xs.append(sample.t)
        ys.append(fn(sample, metric))
    return xs, ys


def extract_shift_markers(samples: Sequence[TimeSeriesSample]) -> list[tuple[float, int]]:
    """Return ``(time_s, new_gear)`` for each upshift/downshift in the session."""
    markers: list[tuple[float, int]] = []
    prev_gear: int | None = None
    for sample in samples:
        gear = sample.hud.gear
        if prev_gear is not None and gear != prev_gear and gear > 0:
            markers.append((sample.t, gear))
        prev_gear = gear
    return markers


def downsample_for_display(
    xs: Sequence[float],
    ys: Sequence[float],
    *,
    max_points: int = 2000,
) -> tuple[list[float], list[float]]:
    """Bucket min/max pairs so polylines stay fast with long sessions."""
    if len(xs) <= max_points or len(xs) == 0:
        return list(xs), list(ys)

    bucket_count = max_points // 2
    span = len(xs) / bucket_count
    out_x: list[float] = []
    out_y: list[float] = []

    for i in range(bucket_count):
        start = int(i * span)
        end = int((i + 1) * span)
        if start >= len(xs):
            break
        end = max(start + 1, min(end, len(xs)))
        chunk_x = xs[start:end]
        chunk_y = ys[start:end]
        out_x.append(chunk_x[len(chunk_x) // 2])
        out_y.append(min(chunk_y))
        out_x.append(chunk_x[len(chunk_x) // 2])
        out_y.append(max(chunk_y))

    return out_x, out_y
