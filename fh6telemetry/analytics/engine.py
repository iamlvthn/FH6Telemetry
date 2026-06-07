"""Aggregating analytics engine.

Owns the individual analysers, feeds each frame through them, and assembles an
immutable :class:`HudState` snapshot for the overlay. All mutable analyser state
lives here and is only touched from the listener thread, so publishing a frozen
snapshot is the single synchronisation point with the GUI.
"""

from __future__ import annotations

import math

from ..config import AppConfig
from ..models import Drivetrain, HudState, TelemetryFrame
from .handling import HandlingAnalyzer
from .lap_timer import LapTimer
from .performance import PerformanceTracker
from .shift_advisor import ShiftAdvisor
from .tires import TireAnalyzer
from .units import ms_to_kph, ms_to_mph, to_g, watts_to_hp, watts_to_kw

# Exponential smoothing for the g-force readout (raw accel is noisy).
_G_SMOOTHING = 0.25


class AnalyticsEngine:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._laps = LapTimer()
        self._shift = ShiftAdvisor(config.shift_light_start, config.shift_light_redline)
        self._tires = TireAnalyzer()
        self._handling = HandlingAnalyzer()
        self._performance = PerformanceTracker()
        self._g_long = 0.0
        self._g_lat = 0.0
        self._g_peak = 0.0
        self._was_active = False

    def reset_session(self) -> None:
        """Clear learned/recorded state (records, power curve, lap traces)."""
        self._laps.reset()
        self._shift.reset()
        self._handling.reset()
        self._performance.reset()
        self._g_peak = 0.0

    def process(self, frame: TelemetryFrame) -> HudState:
        # Auto-reset learned state when a fresh race/session begins.
        if frame.is_active and not self._was_active:
            self._laps.reset()
            self._handling.reset()
        self._was_active = frame.is_active

        g_long, g_lat, g_total = self._update_gforce(frame)
        shift = self._shift.update(frame)
        tires = self._tires.update(frame)
        handling = self._handling.update(frame)
        laps = self._laps.update(frame)
        perf = self._performance.update(frame, g_total)

        return HudState(
            connected=True,
            active=frame.is_active,
            speed_kph=ms_to_kph(frame.speed),
            speed_mph=ms_to_mph(frame.speed),
            rpm=frame.current_engine_rpm,
            max_rpm=frame.engine_max_rpm,
            idle_rpm=frame.engine_idle_rpm,
            rpm_fraction=frame.rpm_fraction,
            gear=frame.gear,
            power_hp=watts_to_hp(frame.power),
            power_kw=watts_to_kw(frame.power),
            torque_nm=frame.torque,
            boost_psi=frame.boost,
            fuel_fraction=frame.fuel,
            drivetrain=Drivetrain.label(frame.drivetrain_type),
            throttle=frame.accel_input / 255.0,
            brake=frame.brake_input / 255.0,
            clutch=frame.clutch_input / 255.0,
            handbrake=frame.handbrake_input / 255.0,
            steer=frame.steer / 127.0,
            shift_light=shift.light,
            should_shift=shift.should_shift,
            optimal_shift_rpm=shift.optimal_rpm,
            g_long=g_long,
            g_lat=g_lat,
            g_total=g_total,
            g_peak=self._g_peak,
            tire_temp_c=tires.temps_c,
            tire_slip=tires.slip,
            tire_status=tires.status,
            balance=handling.balance,
            balance_label=handling.label,
            current_lap=laps.current_lap,
            last_lap=laps.last_lap,
            best_lap=laps.best_lap,
            lap_number=laps.lap_number,
            race_position=laps.race_position,
            delta=laps.delta,
            delta_valid=laps.delta_valid,
            top_speed_kph=perf.top_speed_kph,
            max_power_hp=perf.max_power_hp,
            accel_runs=perf.runs,
            active_run_label=perf.active_label,
            distance_km=frame.distance_traveled / 1000.0,
        )

    def _update_gforce(self, frame: TelemetryFrame) -> tuple[float, float, float]:
        # Forza local frame: X = lateral (right+), Z = longitudinal (forward+).
        target_long = to_g(frame.accel_z)
        target_lat = to_g(frame.accel_x)
        self._g_long += (target_long - self._g_long) * _G_SMOOTHING
        self._g_lat += (target_lat - self._g_lat) * _G_SMOOTHING
        g_total = math.hypot(self._g_long, self._g_lat)
        self._g_peak = max(self._g_peak, g_total)
        return self._g_long, self._g_lat, g_total
