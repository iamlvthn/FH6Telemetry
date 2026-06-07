# Project Context — FH6Telemetry

This document is the single source of truth for the app's purpose, architecture
and feature set. Keep it updated when features are added so future work does not
drift from the original design.

## Purpose

Receive Forza Horizon 6 "Data Out" UDP telemetry, derive useful driving
analytics in real time, and present them in a compact, transparent, always-on-top
overlay suitable for viewing during gameplay.

## Core architecture

Three decoupled layers connected by immutable data structures:

```
UDP datagram
   │  (network thread)
   ▼
parser.parse()  ──►  TelemetryFrame  ──►  AnalyticsEngine.process()  ──►  HudState
                                                                              │
                                                            queued Qt signal  │  (only thread boundary)
                                                                              ▼
                                                                      OverlayWindow (GUI thread)
```

- **Thread model**: a single daemon thread receives packets, decodes them and
  runs analytics. The resulting immutable `HudState` is published to the GUI
  thread through one queued Qt signal. The GUI never locks; analytics mutable
  state is owned exclusively by the listener thread. Session resets are
  requested via a `threading.Event` the listener observes, so the engine is
  never mutated from two threads.

## Modules

| Module | Responsibility | Notes |
|--------|----------------|-------|
| `models.py` | `TelemetryFrame` (raw decoded) and `HudState` (display-ready) | `HudState` is frozen for safe cross-thread publishing |
| `parser.py` | Decode + encode every Forza wire format | Offset tables compiled into `struct.Struct` |
| `network.py` | `UDPTelemetryListener` daemon thread | Socket timeout drives a connected/disconnected status |
| `config.py` | `AppConfig` with JSON override file | `config.local.json`, git-ignored |
| `analytics/units.py` | Pure unit conversions | km/h, mph, hp, kW, °C, g |
| `analytics/lap_timer.py` | Lap detection + distance-indexed predictive delta | Stores best-lap trace |
| `analytics/shift_advisor.py` | Learns power curve, recommends upshift, drives shift light | Bucketed RPM→power map |
| `analytics/tires.py` | Tyre temp classification + slip magnitude | Operating-window thresholds |
| `analytics/handling.py` | Understeer/oversteer from per-axle slip angles | Smoothed, normalised −1..1 |
| `analytics/performance.py` | Acceleration runs + session records | 0-100/0-200/100-200/¼-mile, top speed, peak power/g |
| `analytics/engine.py` | Orchestrates analysers, builds `HudState`, computes g-force | Auto-resets per-session state on race start |
| `overlay/theme.py` | Palette, fonts, time/delta formatting | |
| `overlay/widgets.py` | Eight custom-painted panels | Panels render only; never compute |
| `overlay/window.py` | Frameless translucent always-on-top window, tray, click-through, drag | Win32 `WS_EX_TRANSPARENT` for pass-through |
| `app.py` | Wiring + thread marshalling | |
| `__main__.py` | CLI entry point | `python -m fh6telemetry` |
| `tools/simulator.py` | Synthetic telemetry generator | Encodes 324-byte Horizon packets |
| `lab/` | Offline analysis workbench | Simulation + time-series graphs (Phase 1+) |
| `lab/scenarios/` | `ScenarioEngine` + drive scenarios | `standing_launch` in Phase 1 |
| `lab/recording/` | `SessionBuffer` ring buffer | 60 s @ 60 Hz default |
| `lab/graphs/` | `TimeSeriesGraph`, `GraphWorkspace` | Dual-axis, markers, 2×2 grid + scrubber |
| `analytics/history.py` | Channel extraction for graphs | speed, rpm, power, g, tyres… |

## Forza "Data Out" packet formats

All values little-endian. Supported sizes and dash offset:

| Size | Game | Dash offset | Notes |
|------|------|-------------|-------|
| 232 | All | — | Sled only (motion) |
| 311 | FM7 | 232 | Sled + Car Dash |
| 324 | FH4/FH5/**FH6** | 244 | Sled + 12-byte Horizon gap + Car Dash + 1 pad byte |
| 331 | FM 2023 | 232 | Adds per-tyre wear + track ordinal at offset 311 |

- Sled = 232 bytes (58 × 4-byte fields).
- Car Dash extension = 79 bytes.
- The Horizon layout precedes the dash with a 12-byte block; its first int is the
  community-decoded car category.
- Forza Horizon does **not** emit tyre wear / track ordinal (FM 2023 only).

FH6 is expected to reuse the 324-byte Horizon layout, which is the encoder's
default and the simulator's output format.

## Feature inventory (keep in sync)

- Core: gear, RPM bar, colour shift light, speed (metric/imperial).
- Inputs: throttle/brake/clutch bars, steering indicator.
- Engine: power (hp), torque (Nm), boost (psi), drivetrain, fuel bar.
- G-force: live traction circle + peak-g ring.
- Tyres: 4-corner temperatures (colour-coded), combined-slip strips.
- Handling: understeer/oversteer balance bar.
- Laps: counter, position, current/last/best, predictive delta to best lap.
- Performance: 0-100, 0-200, 100-200, ¼-mile, top speed, peak power.
- Shift advisor: learned optimal upshift RPM + flashing limit light.
- Overlay UX: single horizontal strip anchored to bottom-centre by default,
  click-through toggle, position lock + drag, reset position, unit toggle,
  session reset, persisted window position — all via the system tray.

## Conventions

- Per-wheel arrays are 4-tuples ordered `(FL, FR, RL, RR)`.
- Analytics never touch Qt; the overlay never computes derived values.
- New display metrics flow as fields on `HudState`; new analysers live under
  `analytics/` and are registered in `AnalyticsEngine`.

## Known limitations / future work

- Car/track ordinals are not mapped to names (no public lookup table bundled).
- Tyre wear is unavailable in Horizon telemetry (FM 2023 only).
- Global hotkeys are not bound; runtime controls live in the tray menu.
