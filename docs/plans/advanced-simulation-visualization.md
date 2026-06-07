# Plan: Advanced Simulation & Visualization Lab

**Branch:** `feature/advanced-sim-viz`  
**Status:** Planning  
**Target:** A dedicated analysis workbench alongside the in-game overlay — richer
physics simulation, time-series performance graphs, and a proper desktop UI for
developing and tuning FH6Telemetry without the game running.

---

## 1. Problem statement

The current stack has two gaps:

| Gap | Today | Desired |
|-----|-------|---------|
| **Simulation** | `tools/simulator.py` is a single-file sine-wave drive model streamed over UDP | Configurable scenarios (launch, circuit, drift, coast-down), scripted inputs, replay of recorded sessions |
| **Visualization** | In-game overlay shows *instantaneous* values only (no history) | Scrollable/zoomable graphs: power curve, speed trace, g-force trace, tyre temps, lap delta |
| **UI** | Overlay is optimised for gameplay (transparent, click-through, 88 px tall) | Separate **Lab** window: tabs, controls, graph panels, scenario picker — normal Qt desktop chrome |

The overlay must stay lightweight. All advanced work lives in a new **Lab**
application that reuses the existing parser, models and analytics layers.

---

## 2. Goals & non-goals

### Goals
- Run offline development and demos without Forza.
- Visualise telemetry **over time** (not just the latest frame).
- Compare runs (e.g. two acceleration attempts, two laps).
- Improve the drive model enough that analytics (shift advisor, lap delta,
  accel runs) behave realistically under test.
- Share one data pipeline: Lab, overlay and simulator all consume
  `TelemetryFrame` → `AnalyticsEngine` → display state.

### Non-goals (this branch)
- 3D track/car rendering.
- Live editing of in-game overlay layout from the Lab.
- FM2023-only fields (tyre wear, track ordinal) unless trivial to add.
- Cloud sync or multiplayer.

---

## 3. Proposed architecture

```
                    ┌─────────────────────────────────────┐
                    │           Lab Application            │
                    │  (fh6telemetry.lab — new package)   │
                    └─────────────────────────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          ▼                           ▼                           ▼
   ScenarioEngine              SessionRecorder              GraphWorkspace
   (physics + scripts)         (ring buffer + export)      (Qt charts / custom)
          │                           │                           │
          └───────────────────────────┴───────────────────────────┘
                                      │
                              TelemetryFrame stream
                                      │
                              AnalyticsEngine (existing)
                                      │
                              HudState + TimeSeriesState (new)
```

### New modules (planned)

| Module | Responsibility |
|--------|----------------|
| `fh6telemetry/lab/` | Lab app entry, main window, tabs |
| `fh6telemetry/lab/scenarios/` | Scenario definitions + `ScenarioEngine` |
| `fh6telemetry/lab/recording/` | `SessionBuffer`, CSV/JSON export, replay |
| `fh6telemetry/lab/graphs/` | Reusable graph widgets (line, scatter, bar) |
| `fh6telemetry/models.py` | Add `TimeSeriesSample`, `SessionSnapshot` |
| `fh6telemetry/analytics/history.py` | Rolling history for graph channels |

### Entry points

```bash
python -m fh6telemetry          # in-game overlay (unchanged)
python -m fh6telemetry.lab      # new analysis workbench
python -m tools.simulator       # kept as thin UDP feeder; delegates to ScenarioEngine
```

---

## 4. Advanced simulation design

### 4.1 Scenario engine

Replace the monolithic `_DriveModel` with a composable engine:

```python
class ScenarioEngine:
    def step(self, dt: float) -> TelemetryFrame: ...
    def reset(self) -> None: ...
    @property
    def scenario_name(self) -> str: ...
```

**Built-in scenarios (v1)**

| ID | Description | Exercises |
|----|-------------|-----------|
| `standing_launch` | 0→max with auto shifts | Accel runs, shift advisor, power curve |
| `circuit_lap` | Oval with braking zones + corners | Lap delta, handling balance, g-force |
| `drift_sweep` | Sustained steer + throttle modulation | Lateral g, slip angles, tyre temps |
| `coast_down` | High speed → stop, no throttle | Drag feel, no false accel triggers |
| `replay` | Playback from recorded CSV/JSON | Regression testing |

### 4.2 Physics improvements (incremental)

Phase A — parameterised longitudinal model:
- Engine torque curve (RPM → Nm lookup table, configurable).
- Gear ratios + final drive + shift delay.
- Aero drag (`F = ½ρCdA v²`) and rolling resistance.
- Brake force curve.

Phase B — simplified lateral:
- Ackermann-ish steer → front slip angle.
- Weight transfer affecting grip (optional, behind a flag).
- Tyre temp model: heat from slip + cooling from speed.

Phase C — scripting:
- YAML/JSON scenario files: `{ "throttle": [[0,0],[2,1],[5,0]], ... }`.
- Keyboard override in Lab UI for manual driving during sim.

### 4.3 Transport modes

The Lab can feed analytics via **direct callback** (no UDP) for lowest latency.
UDP mode remains for testing the full overlay path.

```
Lab ──direct──► AnalyticsEngine     (preferred in Lab)
Lab ──UDP─────► UDPTelemetryListener (overlay integration test)
```

---

## 5. Performance graphs & visualization

### 5.1 Time-series buffer

```python
@dataclass(frozen=True)
class TimeSeriesSample:
    t: float          # seconds since session start
    frame: TelemetryFrame
    hud: HudState
```

`SessionBuffer` — fixed-capacity deque (default 60 s @ 60 Hz = 3600 samples):
- Append on every frame.
- Export to CSV (reuse v2-style column naming from community tools).
- Slice by time range for graph X-axis.

### 5.2 Graph channels (v1)

| Graph | Y axis | Use |
|-------|--------|-----|
| **Speed** | km/h or mph | Lap shape, top speed |
| **RPM + shift markers** | rpm | Shift advisor validation |
| **Power & torque** | hp, Nm (dual axis) | Power-band learning |
| **Pedals** | 0–100 % | Input correlation |
| **G-force** | long / lat / total | Handling events |
| **Tyre temps** | 4 lines (FL/FR/RL/RR) | Heat cycle |
| **Lap delta** | seconds | Predictive delta accuracy |
| **Handling balance** | −1…+1 | Understeer/oversteer trace |

### 5.3 Rendering approach

**Option chosen:** custom `QWidget` painters with ring-buffer polylines (no new
heavy deps). PySide6 `QtCharts` is optional behind a feature flag if we need
crosshair zoom later.

Graph widget API:

```python
class TimeSeriesGraph(QWidget):
    def set_series(self, name: str, xs: list[float], ys: list[float], color: QColor) -> None
    def set_x_range(self, start: float, end: float) -> None  # zoom
    def set_follow_live(self, enabled: bool) -> None         # auto-scroll
```

Performance targets:
- 60 Hz ingest, 30 Hz graph repaint (decouple with `QTimer`).
- Downsample for display when >2000 points visible (min/max bucket).

---

## 6. Lab UI design

### 6.1 Layout (desktop window, ~1280×800)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  FH6Telemetry Lab          [Scenario ▼] [▶] [⏸] [↻]   Speed: 2×  [UDP ☐] │
├──────────────────────────────┬───────────────────────────────────────────┤
│  Live HUD strip (reuse       │  Graph grid (2×2 or tabbed):              │
│  overlay panels, optional)   │  ┌─────────────┬─────────────┐            │
│                              │  │ Speed       │ Power/RPM   │            │
│  Session stats               │  ├─────────────┼─────────────┤            │
│  · elapsed / distance        │  │ G-force     │ Tyre temps  │            │
│  · best lap / top speed      │  └─────────────┴─────────────┘            │
│  · accel run table           │  [Timeline scrubber ────────────●────]    │
├──────────────────────────────┴───────────────────────────────────────────┤
│  Log / export: [Save CSV] [Load replay] [Compare session…]                 │
└──────────────────────────────────────────────────────────────────────────┘
```

### 6.2 UX principles
- Dark theme consistent with overlay palette (`overlay/theme.py` → shared
  `theme.py` at package root).
- Play/pause/scrub without blocking the sim thread.
- Graph click → vertical cursor + tooltip showing values at that time.
- Scenario parameters editable in a side drawer (gear ratios, redline, track
  length).

### 6.3 Reuse strategy
- Extract `overlay/widgets.py` panels into importable components (no change to
  paint logic; Lab embeds them in a `QWidget` container).
- Do **not** enable click-through or always-on-top in Lab.

---

## 7. Implementation phases

### Phase 0 — Branch scaffolding *(this commit)*
- [x] Plan document
- [ ] Empty `fh6telemetry/lab/` package with README stub
- [ ] Milestone labels / checklist in this file

### Phase 1 — Foundation (est. 2–3 sessions)
- [ ] `SessionBuffer` + `TimeSeriesSample`
- [ ] `analytics/history.py` — channel extraction helpers
- [ ] `TimeSeriesGraph` base widget (one channel, live scroll)
- [ ] `ScenarioEngine` interface + port `standing_launch` from current sim
- [ ] `python -m fh6telemetry.lab` opens empty window with one graph

### Phase 2 — Simulation depth (est. 3–4 sessions)
- [ ] Torque curve + gear model refactor
- [ ] `circuit_lap` and `drift_sweep` scenarios
- [ ] Scenario picker + play/pause/speed multiplier
- [ ] Direct-feed path into `AnalyticsEngine` (no UDP)
- [ ] CSV export

### Phase 3 — Graph suite (est. 2–3 sessions)
- [ ] Graph grid with 4 default charts
- [ ] Timeline scrubber + follow-live toggle
- [ ] Dual-axis power/RPM graph with shift markers
- [ ] Lap delta + handling traces

### Phase 4 — Lab UI polish (est. 2 sessions)
- [ ] Embedded HUD strip + session stats panel
- [ ] Scenario parameter drawer
- [ ] CSV replay + A/B session compare (overlay two speed traces)
- [ ] UDP bridge toggle for overlay integration testing

### Phase 5 — Integration & docs
- [ ] Update `README.md`, `project_context.md`, `changelog.md`
- [ ] Replace `tools/simulator.py` internals with `ScenarioEngine` adapter
- [ ] Screenshot/GIF for docs
- [ ] Merge `feature/advanced-sim-viz` → `main`

---

## 8. Dependencies

| Package | Purpose | Required |
|---------|---------|----------|
| `PySide6` | Lab UI + graphs | Yes (already) |
| `numpy` | Optional downsampling / CSV | Defer until needed |
| `pyqtgraph` | Alternative fast plots | **No** — prefer zero new deps first |

---

## 9. Testing strategy

| Layer | Test |
|-------|------|
| `ScenarioEngine` | Deterministic `step()` snapshots at fixed `dt` |
| `SessionBuffer` | Capacity eviction, export round-trip |
| `TimeSeriesGraph` | Headless `grab()` smoke test (CI-friendly) |
| Integration | Lab + `standing_launch` → accel runs populate within N seconds |
| Regression | Replay a golden CSV; assert lap count and peak speed ±ε |

---

## 10. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Graph repaint too slow at 60 Hz | 30 Hz repaint timer + display downsampling |
| Physics model unrealistic | Validate against real FH sessions once available; tune scenarios |
| Scope creep (3D, maps) | Strict non-goals; phase gates |
| Overlay/Lab theme drift | Extract shared palette to `fh6telemetry/theme.py` in Phase 4 |

---

## 11. Open questions

1. **Compare mode** — overlay two sessions on one graph, or side-by-side panels?
   *Proposal:* overlay with legend (same graph) for v1.
2. **Recording format** — CSV only, or JSON lines for full frame fidelity?
   *Proposal:* CSV for graphs; optional JSONL for full replay in Phase 4.
3. **Merge strategy** — ship Lab behind `python -m fh6telemetry.lab` only, no
   change to default overlay install path.

---

## 12. Success criteria (merge-ready)

- [ ] Lab launches on Windows with no game running.
- [ ] At least 3 scenarios selectable; `circuit_lap` completes ≥1 lap with valid
      delta.
- [ ] 4 live graphs update during simulation without UI stutter.
- [ ] Session exportable to CSV; replay reproduces peak speed within 5 %.
- [ ] Overlay path still works unchanged via UDP.
- [ ] Documentation updated.

---

*Next action on this branch: Phase 1 — scaffold `fh6telemetry/lab/`, implement
`SessionBuffer` and a single `TimeSeriesGraph` wired to `standing_launch`.*
