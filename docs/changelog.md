# Changelog

All notable changes to FH6Telemetry are documented here.

## [0.2.0] — Lab workbench

### Added
- **`fh6telemetry.lab`** — offline simulation and visualization workbench
  (`python -m fh6telemetry.lab`).
- `ScenarioEngine` with `standing_launch`, `circuit_lap`, and `drift_sweep`
  scenarios sharing a torque-curve `VehicleModel`.
- `SessionBuffer`, CSV export/import, `ReplayPlayer`, and `TimeSeriesGraph` /
  `GraphWorkspace` (2×2 charts, timeline scrubber, dual-axis power/RPM with shift
  markers, delta/balance row).
- Lab sidebar: embedded overlay HUD strip, session stats, scenario parameter
  drawer (redline, track length, power scale).
- CSV A/B compare overlay on the speed chart; optional **UDP bridge** to feed
  the in-game overlay from the Lab.
- `analytics/history.py` channel extractors; `TimeSeriesSample` model.
- Development plan: `docs/plans/advanced-simulation-visualization.md`.

### Changed
- `tools/simulator.py` now delegates to `ScenarioEngine` (same physics as Lab);
  adds `--scenario` flag (default `circuit_lap`).
- Overlay layout is a single horizontal strip (~1155×88) anchored to **bottom
  centre** of the screen (24 px margin); tray **Reset position** action.
- Version bumped to **0.2.0**.

## [0.1.0] — Initial release

### Added
- Multi-format Forza "Data Out" UDP decoder (Sled 232, FM7 Dash 311, Horizon
  324, FM 2023 Dash 331) with a matching encoder.
- Threaded UDP listener with connected/disconnected status.
- Analytics engine: predictive lap delta, shift advisor, tyre/handling analysis,
  acceleration runs, g-force smoothing.
- Transparent, always-on-top **PySide6 overlay** with eight compact panels.
- Windows click-through, tray controls, metric/imperial toggle, JSON config.
- CLI entry point (`python -m fh6telemetry`).
- Project documentation: `README.md`, `docs/project_context.md`.
