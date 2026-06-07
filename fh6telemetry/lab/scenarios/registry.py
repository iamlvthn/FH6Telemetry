"""Shared scenario registry for the Lab and UDP simulator."""

from __future__ import annotations

from .circuit_lap import CircuitLapScenario
from .drift_sweep import DriftSweepScenario
from .engine import ScenarioEngine
from .standing_launch import StandingLaunchScenario


def build_scenario_engine() -> ScenarioEngine:
    """Return an engine with every built-in Lab scenario registered."""
    return ScenarioEngine(
        [
            StandingLaunchScenario(),
            CircuitLapScenario(),
            DriftSweepScenario(),
        ]
    )
