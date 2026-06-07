"""Load exported Lab sessions back from CSV."""

from __future__ import annotations

import csv
from pathlib import Path

from ...models import HudState, TelemetryFrame, TimeSeriesSample
def _float(value: str, default: float = 0.0) -> float:
    value = value.strip()
    if not value:
        return default
    return float(value)


def _int(value: str, default: int = 0) -> int:
    value = value.strip()
    if not value:
        return default
    return int(float(value))


def _sample_from_row(row: dict[str, str]) -> TimeSeriesSample:
    t = _float(row["t_s"])
    speed_kph = _float(row["speed_kph"])
    speed_mph = _float(row["speed_mph"])
    rpm = _float(row["rpm"])
    gear = _int(row["gear"])
    throttle = _float(row["throttle_pct"]) / 100.0
    brake = _float(row["brake_pct"]) / 100.0
    power_hp = _float(row["power_hp"])
    torque_nm = _float(row["torque_nm"])
    g_long = _float(row["g_long"])
    g_lat = _float(row["g_lat"])
    g_total = _float(row["g_total"])
    balance = _float(row["balance"])
    delta_raw = row.get("delta_s", "").strip()
    delta_valid = bool(delta_raw)
    delta = _float(delta_raw) if delta_valid else 0.0
    lap_number = _int(row["lap"])
    distance_km = _float(row["distance_km"])
    temps = (
        _float(row["tire_fl_c"]),
        _float(row["tire_fr_c"]),
        _float(row["tire_rl_c"]),
        _float(row["tire_rr_c"]),
    )

    hud = HudState(
        connected=True,
        active=True,
        speed_kph=speed_kph,
        speed_mph=speed_mph,
        rpm=rpm,
        gear=gear,
        power_hp=power_hp,
        torque_nm=torque_nm,
        throttle=throttle,
        brake=brake,
        g_long=g_long,
        g_lat=g_lat,
        g_total=g_total,
        balance=balance,
        delta=delta,
        delta_valid=delta_valid,
        lap_number=lap_number,
        distance_km=distance_km,
        tire_temp_c=temps,
    )

    frame = TelemetryFrame(
        is_race_on=1,
        current_engine_rpm=rpm,
        speed=speed_kph / 3.6,
        power=power_hp * 745.699872,
        torque=torque_nm,
        accel_input=int(throttle * 255),
        brake_input=int(brake * 255),
        gear=gear,
        distance_traveled=distance_km * 1000.0,
        lap_number=lap_number,
        has_dash=True,
    )
    return TimeSeriesSample(t=t, frame=frame, hud=hud)


def load_session_csv(path: str | Path) -> list[TimeSeriesSample]:
    """Parse a session CSV exported by :mod:`export` back into samples."""
    target = Path(path)
    samples: list[TimeSeriesSample] = []
    with target.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return samples
        for row in reader:
            samples.append(_sample_from_row(row))
    return samples
