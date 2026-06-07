"""Registry and runner for synthetic drive scenarios."""

from __future__ import annotations

from ...models import TelemetryFrame
from .base import Scenario


class ScenarioEngine:
    """Owns the active scenario and exposes a uniform stepping API."""

    def __init__(self, scenarios: list[Scenario] | None = None) -> None:
        self._scenarios: dict[str, Scenario] = {}
        self._current: Scenario | None = None
        for scenario in scenarios or []:
            self.register(scenario)

    def register(self, scenario: Scenario) -> None:
        self._scenarios[scenario.id] = scenario
        if self._current is None:
            self._current = scenario

    def ids(self) -> list[str]:
        return list(self._scenarios.keys())

    def label_for(self, scenario_id: str) -> str:
        scenario = self._scenarios.get(scenario_id)
        return scenario.label if scenario else scenario_id

    def set_scenario(self, scenario_id: str) -> None:
        if scenario_id not in self._scenarios:
            raise KeyError(f"unknown scenario: {scenario_id}")
        self._current = self._scenarios[scenario_id]
        self._current.reset()

    @property
    def scenario_id(self) -> str:
        return self._current.id if self._current else ""

    @property
    def scenario_name(self) -> str:
        return self._current.label if self._current else ""

    def reset(self) -> None:
        if self._current is not None:
            self._current.reset()

    def step(self, dt: float) -> TelemetryFrame:
        if self._current is None:
            raise RuntimeError("no scenario selected")
        return self._current.step(dt)
