"""FH6Telemetry Lab main window."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
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

from PySide6.QtCore import QTimer

from ..analytics import AnalyticsEngine
from ..analytics.history import extract_channel
from ..config import AppConfig
from ..overlay import theme
from .graphs import TimeSeriesGraph
from .recording import SessionBuffer, export_session_csv
from .scenarios import (
    CircuitLapScenario,
    DriftSweepScenario,
    ScenarioEngine,
    StandingLaunchScenario,
)

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
    """Desktop workbench: run scenarios and visualise speed over time."""

    SIM_HZ = 60.0
    GRAPH_HZ = 30.0

    def __init__(self, config: AppConfig | None = None) -> None:
        super().__init__()
        self._config = config or AppConfig()
        self._engine = AnalyticsEngine(self._config)
        self._scenario_engine = _default_scenarios()
        self._buffer = SessionBuffer()
        self._running = False
        self._base_dt = 1.0 / self.SIM_HZ
        self._speed_mult = 1.0

        self.setWindowTitle("FH6Telemetry Lab")
        self.resize(960, 520)
        self._build_ui()
        self._wire_timers()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

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

        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self._export_csv)
        toolbar.addWidget(export_btn)

        toolbar.addStretch()
        self._status = QLabel("Ready")
        self._status.setStyleSheet(
            f"color: rgb({theme.TEXT_DIM.red()}, {theme.TEXT_DIM.green()}, {theme.TEXT_DIM.blue()});"
        )
        toolbar.addWidget(self._status)
        layout.addLayout(toolbar)

        unit = "km/h" if self._config.use_metric else "mph"
        self._graph = TimeSeriesGraph(title=f"Speed ({unit})")
        self._graph.set_y_unit(unit)
        self._graph.set_follow_live(True, window_seconds=30.0)
        layout.addWidget(self._graph, stretch=1)

        self._stats = QLabel("Distance: 0.0 km  |  Top speed: 0  |  Samples: 0")
        layout.addWidget(self._stats)

    def _wire_timers(self) -> None:
        self._sim_timer = QTimer(self)
        self._sim_timer.setInterval(int(1000 / self.SIM_HZ))
        self._sim_timer.timeout.connect(self._sim_tick)

        self._graph_timer = QTimer(self)
        self._graph_timer.setInterval(int(1000 / self.GRAPH_HZ))
        self._graph_timer.timeout.connect(self._refresh_graph)
        self._graph_timer.start()

    def _on_scenario_changed(self, _index: int) -> None:
        sid = self._scenario_combo.currentData()
        if sid:
            self._scenario_engine.set_scenario(sid)
            self._reset_session()

    def _on_speed_changed(self, _index: int) -> None:
        value = self._speed_combo.currentData()
        if value:
            self._speed_mult = float(value)

    def _toggle_play(self) -> None:
        if self._running:
            self._running = False
            self._sim_timer.stop()
            self._play_btn.setText("Play")
            self._status.setText("Paused")
        else:
            self._running = True
            self._sim_timer.start()
            self._play_btn.setText("Pause")
            self._status.setText(
                f"Running — {self._scenario_engine.scenario_name} @ {self._speed_combo.currentText()}"
            )

    def _reset_session(self) -> None:
        was_running = self._running
        if was_running:
            self._toggle_play()
        self._scenario_engine.reset()
        self._engine.reset_session()
        self._buffer.clear()
        self._graph.clear_series()
        self._refresh_graph()
        self._update_stats()
        self._status.setText("Reset")
        if was_running:
            self._toggle_play()

    def _sim_tick(self) -> None:
        dt = self._base_dt * self._speed_mult
        frame = self._scenario_engine.step(dt)
        hud = self._engine.process(frame)
        self._buffer.append(frame, hud, dt=dt)

    def _refresh_graph(self) -> None:
        samples = self._buffer.samples()
        xs, ys = extract_channel(samples, "speed", metric=self._config.use_metric)
        self._graph.set_series("speed", xs, ys, theme.ACCENT)
        self._update_stats()

    def _update_stats(self) -> None:
        samples = self._buffer.samples()
        if not samples:
            self._stats.setText("Distance: 0.0 km  |  Top speed: 0  |  Samples: 0")
            return
        last = samples[-1].hud
        unit = "km/h" if self._config.use_metric else "mph"
        top = last.top_speed_kph if self._config.use_metric else last.top_speed_kph * 0.621371
        lap = f"  |  Lap {last.lap_number}" if last.lap_number > 0 else ""
        self._stats.setText(
            f"Distance: {last.distance_km:.2f} km  |  "
            f"Top speed: {top:.0f} {unit}{lap}  |  "
            f"Samples: {self._buffer.count}"
        )

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
