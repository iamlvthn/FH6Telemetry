"""Session export helpers."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TextIO

from ...models import TimeSeriesSample

CSV_COLUMNS = (
    "t_s",
    "speed_kph",
    "speed_mph",
    "rpm",
    "gear",
    "throttle_pct",
    "brake_pct",
    "power_hp",
    "torque_nm",
    "g_long",
    "g_lat",
    "g_total",
    "balance",
    "delta_s",
    "lap",
    "distance_km",
    "tire_fl_c",
    "tire_fr_c",
    "tire_rl_c",
    "tire_rr_c",
)


def _row(sample: TimeSeriesSample) -> list[float | int | str]:
    h = sample.hud
    delta = h.delta if h.delta_valid else ""
    return [
        round(sample.t, 4),
        round(h.speed_kph, 2),
        round(h.speed_mph, 2),
        round(h.rpm, 1),
        h.gear,
        round(h.throttle * 100.0, 1),
        round(h.brake * 100.0, 1),
        round(h.power_hp, 1),
        round(h.torque_nm, 1),
        round(h.g_long, 3),
        round(h.g_lat, 3),
        round(h.g_total, 3),
        round(h.balance, 3),
        delta if delta == "" else round(delta, 4),
        h.lap_number,
        round(h.distance_km, 4),
        round(h.tire_temp_c[0], 1),
        round(h.tire_temp_c[1], 1),
        round(h.tire_temp_c[2], 1),
        round(h.tire_temp_c[3], 1),
    ]


def write_session_csv(samples: list[TimeSeriesSample] | tuple[TimeSeriesSample, ...], stream: TextIO) -> None:
    """Write samples to an open text stream in CSV format."""
    writer = csv.writer(stream)
    writer.writerow(CSV_COLUMNS)
    for sample in samples:
        writer.writerow(_row(sample))


def export_session_csv(
    samples: list[TimeSeriesSample] | tuple[TimeSeriesSample, ...],
    path: str | Path,
) -> Path:
    """Persist a session to disk and return the resolved path."""
    target = Path(path)
    with target.open("w", newline="", encoding="utf-8") as handle:
        write_session_csv(samples, handle)
    return target.resolve()
