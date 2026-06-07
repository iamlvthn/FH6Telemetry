"""FH6Telemetry - Forza Horizon 6 telemetry analytics and in-game overlay.

The package is organised into independent layers so each concern can be
developed and tested in isolation:

* ``models``    - immutable telemetry/HUD data structures.
* ``parser``    - decodes raw Forza "Data Out" UDP datagrams into frames.
* ``network``   - threaded UDP listener feeding the analytics engine.
* ``analytics`` - derives useful metrics (laps, shifts, tyres, g-forces...).
* ``overlay``   - PySide6 transparent, always-on-top in-game HUD.
* ``app``       - wires the layers together into a runnable application.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.2.0"
