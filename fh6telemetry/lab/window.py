"""FH6Telemetry Lab main window."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..analytics import AnalyticsEngine
from ..config import AppConfig
from ..models import HudState, TimeSeriesSample
from ..overlay import theme
from .graphs import GraphWorkspace
from .recording import SessionBuffer, export_session_csv, load_session_csv
from .replay import ReplayPlayer
from .scenarios import (
    CircuitLapScenario,
    DriftSweepScenario,
    ScenarioEngine,
    StandingLaunchScenario,
)
from .udp_bridge import UdpBridge
from .ui import HudStripWidget, ParamsDrawerWidget, StatsPanelWidget

_SPEED_OPTIONS = [
    ("0.5×", 0.5),
    ("1×", 1.0),
    ("2×", 2.0),
    ("4×", 4.0),
]


def _default_scenarios() -> ScenarioEngine:
    return ScenarioEngine(
        [
            StandingLaunchScenario(),
            CircuitLapScenario(),
            DriftSweepScenario(),
        ]
    )


class LabWindow(QMainWindow):
    """Desktop workbench: simulate, replay, and visualise telemetry."""

    SIM_HZ = 60.0
    GRAPH_HZ = 30.0

    def __init__(self, config: AppConfig | None = None) -> None:
        super().__init__()
        self._config = config or AppConfig()
        self._engine = AnalyticsEngine(self._config)
        self._scenario_engine = _default_scenarios()
        self._buffer = SessionBuffer()
        self._udp = UdpBridge(host="127.0.0.1", port=self._config.port)
        self._running = False
        self._base_dt = 1.0 / self.SIM_HZ
        self._speed_mult = 1.0
        self._mode = "sim"
        self._replay: ReplayPlayer | None = None
        self._compare_samples: list[TimeSeriesSample] | None = None
        self._last_hud = HudState()

        self.setWindowTitle("FH6Telemetry Lab")
        self.resize(1320, 860)
        self._build_ui()
        self._wire_timers()
        self._params.sync_from_scenario()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Scenario"))
        self._scenario_combo = QComboBox()
        for sid in self._scenario_engine.ids():
            self._scenario_combo.addItem(self._scenario_engine.label_for(sid), sid)
        self._scenario_combo.currentIndexChanged.connect(self._on_scenario_changed)
        toolbar.addWidget(self._scenario_combo)

        self._play_btn = QPushButton("Play")
        self._play_btn.clicked.connect(self._toggle_play)
        toolbar.addWidget(self._play_btn)

        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self._reset_session)
        toolbar.addWidget(reset_btn)

        toolbar.addWidget(QLabel("Speed"))
        self._speed_combo = QComboBox()
        for label, value in _SPEED_OPTIONS:
            self._speed_combo.addItem(label, value)
        self._speed_combo.setCurrentIndex(1)
        self._speed_combo.currentIndexChanged.connect(self._on_speed_changed)
        toolbar.addWidget(self._speed_combo)

        load_btn = QPushButton("Load CSV")
        load_btn.clicked.connect(self._load_csv)
        toolbar.addWidget(load_btn)

        compare_btn = QPushButton("Load compare")
        compare_btn.clicked.connect(self._load_compare)
        toolbar.addWidget(compare_btn)

        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self._export_csv)
        toolbar.addWidget(export_btn)

        self._udp_check = QCheckBox("UDP bridge")
        self._udp_check.setToolTip(
            f"Stream telemetry to 127.0.0.1:{self._config.port} for overlay testing"
        )
        self._udp_check.toggled.connect(self._udp.set_enabled)
        toolbar.addWidget(self._udp_check)

        toolbar.addStretch()
        self._status = QLabel("Ready")
        self._status.setStyleSheet(
            f"color: rgb({theme.TEXT_DIM.red()}, {theme.TEXT_DIM.green()}, {theme.TEXT_DIM.blue()});"
        )
        toolbar.addWidget(self._status)
        outer.addLayout(toolbar)

        body = QHBoxLayout()
        body.setSpacing(12)

        sidebar = QVBoxLayout()
        sidebar.setSpacing(10)
        self._hud = HudStripWidget()
        sidebar.addWidget(self._hud)
        self._stats = StatsPanelWidget()
        sidebar.addWidget(self._stats)
        self._params = ParamsDrawerWidget(self._scenario_engine, on_apply=self._on_params_applied)
        sidebar.addWidget(self._params)
        sidebar.addStretch()

        sidebar_host = QWidget()
        sidebar_host.setLayout(sidebar)
        sidebar_host.setFixedWidth(500)
        body.addWidget(sidebar_host)

        self._workspace = GraphWorkspace(metric=self._config.use_metric)
        body.addWidget(self._workspace, stretch=1)
        outer.addLayout(body, stretch=1)

    def _wire_timers(self) -> None:
        self._sim_timer = QTimer(self)
        self._sim_timer.setInterval(int(1000 / self.SIM_HZ))
        self._sim_timer.timeout.connect(self._sim_tick)

        self._graph_timer = QTimer(self)
        self._graph_timer.setInterval(int(1000 / self.GRAPH_HZ))
        self._graph_timer.timeout.connect(self._refresh_graphs)
        self._graph_timer.start()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._udp.close()
        super().closeEvent(event)

    def _on_scenario_changed(self, _index: int) -> None:
        sid = self._scenario_combo.currentData()
        if sid:
            self._enter_sim_mode()
            self._scenario_engine.set_scenario(sid)
            self._params.sync_from_scenario()
            self._reset_session()

    def _on_speed_changed(self, _index: int) -> None:
        value = self._speed_combo.currentData()
        if value:
            self._speed_mult = float(value)

    def _on_params_applied(self) -> None:
        self._status.setText("Parameters applied — reset recommended")
        self._params.sync_from_scenario()

    def _enter_sim_mode(self) -> None:
        self._mode = "sim"
        self._replay = None

    def _toggle_play(self) -> None:
        if self._running:
            self._running = False
            self._sim_timer.stop()
            self._play_btn.setText("Play")
            self._status.setText("Paused")
        else:
            if self._mode == "replay" and self._replay is not None:
                if self._replay.finished:
                    self._buffer.clear()
                    self._replay.reset()
            self._running = True
            self._sim_timer.start()
            self._play_btn.setText("Pause")
            label = "Replay" if self._mode == "replay" else self._scenario_engine.scenario_name
            self._status.setText(f"Running — {label} @ {self._speed_combo.currentText()}")

    def _reset_session(self) -> None:
        was_running = self._running
        if was_running:
            self._toggle_play()
        if self._mode == "sim":
            self._scenario_engine.reset()
            self._engine.reset_session()
        elif self._replay is not None:
            self._replay.reset()
        self._buffer.clear()
        self._workspace.clear()
        self._last_hud = HudState()
        self._hud.apply_state(self._last_hud)
        self._stats.clear()
        self._status.setText("Reset")
        if was_running:
            self._toggle_play()

    def _sim_tick(self) -> None:
        if self._mode == "replay" and self._replay is not None:
            sample = self._replay.step()
            if sample is None:
                self._toggle_play()
                self._status.setText("Replay finished")
                return
            self._buffer.append_sample(sample)
            self._last_hud = sample.hud
            self._hud.apply_state(sample.hud)
            self._udp.send(sample.frame)
            return

        dt = self._base_dt * self._speed_mult
        frame = self._scenario_engine.step(dt)
        hud = self._engine.process(frame)
        self._buffer.append(frame, hud, dt=dt)
        self._last_hud = hud
        self._hud.apply_state(hud)
        self._udp.send(frame)

    def _refresh_graphs(self) -> None:
        samples = self._buffer.samples()
        self._workspace.refresh(samples, compare_samples=self._compare_samples)
        if samples:
            self._stats.update_from(
                samples[-1].hud,
                elapsed=self._buffer.elapsed,
                metric=self._config.use_metric,
            )

    def _load_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load session CSV", str(Path.cwd()), "CSV (*.csv)")
        if not path:
            return
        try:
            samples = load_session_csv(path)
        except (OSError, ValueError, KeyError) as exc:
            QMessageBox.warning(self, "Load CSV", f"Could not load file:\n{exc}")
            return
        if not samples:
            QMessageBox.information(self, "Load CSV", "File contains no samples.")
            return
        if self._running:
            self._toggle_play()
        self._mode = "replay"
        self._replay = ReplayPlayer(samples)
        self._buffer.load_samples(samples)
        self._last_hud = samples[-1].hud
        self._hud.apply_state(self._last_hud)
        self._refresh_graphs()
        self._status.setText(f"Loaded {len(samples)} samples — press Play to animate")

    def _load_compare(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load compare CSV", str(Path.cwd()), "CSV (*.csv)"
        )
        if not path:
            return
        try:
            self._compare_samples = load_session_csv(path)
        except (OSError, ValueError, KeyError) as exc:
            QMessageBox.warning(self, "Load compare", f"Could not load file:\n{exc}")
            return
        if not self._compare_samples:
            QMessageBox.information(self, "Load compare", "File contains no samples.")
            return
        self._refresh_graphs()
        self._status.setText(f"Compare overlay: {len(self._compare_samples)} samples on speed chart")

    def _export_csv(self) -> None:
        samples = self._buffer.samples()
        if not samples:
            QMessageBox.information(self, "Export CSV", "No samples to export. Run a simulation first.")
            return
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"fh6_session_{stamp}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export session CSV",
            str(Path.cwd() / default_name),
            "CSV files (*.csv)",
        )
        if not path:
            return
        target = export_session_csv(samples, path)
        self._status.setText(f"Exported {len(samples)} rows → {target.name}")
        QMessageBox.information(self, "Export CSV", f"Saved {len(samples)} samples to:\n{target}")
