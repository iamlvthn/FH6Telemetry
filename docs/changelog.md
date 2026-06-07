# Changelog

All notable changes to FH6Telemetry are documented here.

## [Unreleased]

### Added
- Development plan for the Advanced Simulation & Visualization Lab on branch
  `feature/advanced-sim-viz` (`docs/plans/advanced-simulation-visualization.md`).
- **Lab Phase 1:** `fh6telemetry.lab` workbench with `ScenarioEngine`,
  `StandingLaunchScenario`, `SessionBuffer`, `TimeSeriesGraph`, and live speed
  chart (`python -m fh6telemetry.lab`).
- `TimeSeriesSample` model, `analytics/history.py` channel extractors.
- **Lab Phase 2:** `VehicleModel` with torque curve, `circuit_lap` and
  `drift_sweep` scenarios, simulation speed multiplier, CSV session export.

### Changed
- Overlay layout is now a single horizontal strip (~1155×88) instead of a tall
  multi-row grid, better suited to bottom-of-screen placement during gameplay.
- Default window position anchors to the **bottom centre** of the primary screen
  (24 px margin). Saved coordinates from dragging still override the anchor.
- Tray menu adds **Reset position (bottom centre)**.

## [0.1.0] — Initial release

### Added
- Multi-format Forza "Data Out" UDP decoder (Sled 232, FM7 Dash 311, Horizon
  324, FM 2023 Dash 331) with a matching encoder used by the test simulator.
- Threaded UDP listener with connected/disconnected status.
- Analytics engine with independent analysers:
  - distance-indexed **predictive lap delta** and lap timing,
  - power-band-learning **shift advisor** with shift light,
  - tyre temperature classification and combined-slip readout,
  - understeer/oversteer **handling balance**,
  - **acceleration runs** (0-100, 0-200, 100-200, ¼-mile) and session records
    (top speed, peak power, peak g),
  - smoothed g-force / traction-circle data.
- Transparent, always-on-top **PySide6 overlay** with eight compact panels.
- Windows click-through (input pass-through), draggable/lockable positioning,
  metric/imperial toggle, session reset and quit — via a system-tray menu.
- CLI entry point (`python -m fh6telemetry`) with host/port/units overrides and
  a JSON config override file.
- `tools/simulator.py` synthetic telemetry generator for offline testing.
- Project documentation: `README.md`, `docs/project_context.md`.
