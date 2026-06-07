"""Runtime configuration for FH6Telemetry.

Defaults are chosen to work out-of-the-box with Forza Horizon's "Data Out"
feature. Settings can be overridden by a ``config.local.json`` file placed in
the current working directory, which is handy for per-machine tweaks (port,
window position, theme) without touching source control.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

DEFAULT_CONFIG_FILENAME = "config.local.json"


@dataclass(slots=True)
class AppConfig:
    """User-tunable application settings."""

    # --- Network ---------------------------------------------------------------
    # Listen on all interfaces so packets from the console/PC reach us. Forza's
    # "Data Out" default port is 5300 but any free 1024-65535 port works.
    host: str = "0.0.0.0"
    port: int = 5300

    # --- Units -----------------------------------------------------------------
    use_metric: bool = True  # km/h + °C when True, mph + °F when False

    # --- Overlay window --------------------------------------------------------
    window_x: int = 40
    window_y: int = 40
    opacity: float = 0.90
    click_through: bool = True  # start in pass-through mode so the game gets input
    locked: bool = False  # when True the overlay cannot be dragged

    # --- Shift advisor ---------------------------------------------------------
    # Fraction of redline at which the shift light begins / turns red.
    shift_light_start: float = 0.85
    shift_light_redline: float = 0.97

    # --- Panel visibility ------------------------------------------------------
    panels: dict[str, bool] = field(
        default_factory=lambda: {
            "core": True,  # gear / rpm / speed
            "inputs": True,  # throttle / brake / clutch
            "power": True,  # power / torque / boost
            "gforce": True,  # traction circle
            "tires": True,  # 4-corner temps + slip
            "handling": True,  # understeer / oversteer balance
            "laps": True,  # lap timing + delta
            "performance": True,  # 0-100, top speed, records
        }
    )

    @classmethod
    def load(cls, path: str | Path | None = None) -> "AppConfig":
        """Load configuration, merging any on-disk overrides over the defaults."""
        config = cls()
        target = Path(path) if path else Path.cwd() / DEFAULT_CONFIG_FILENAME
        if not target.exists():
            return config
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return config
        config.apply(data)
        return config

    def apply(self, data: dict) -> None:
        """Apply a dict of overrides, ignoring unknown keys for forward-compat."""
        valid = {f for f in self.__slots__}  # type: ignore[attr-defined]
        for key, value in data.items():
            if key == "panels" and isinstance(value, dict):
                self.panels.update({k: bool(v) for k, v in value.items()})
            elif key in valid:
                setattr(self, key, value)

    def save(self, path: str | Path | None = None) -> None:
        """Persist current settings to disk (used to remember window position)."""
        target = Path(path) if path else Path.cwd() / DEFAULT_CONFIG_FILENAME
        try:
            target.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        except OSError:
            # Persistence is best-effort; never crash the overlay over it.
            pass
