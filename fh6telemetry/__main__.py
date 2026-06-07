"""Command-line entry point: ``python -m fh6telemetry``.

Loads configuration, applies any command-line overrides, then launches the
overlay application.
"""

from __future__ import annotations

import argparse
import sys

from .app import Application
from .config import AppConfig


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="fh6telemetry",
        description="Forza Horizon 6 telemetry overlay.",
    )
    parser.add_argument("--host", help="Interface to bind (default from config).")
    parser.add_argument("--port", type=int, help="UDP port Forza 'Data Out' targets.")
    parser.add_argument(
        "--imperial",
        action="store_true",
        help="Use mph / Fahrenheit instead of km/h / Celsius.",
    )
    parser.add_argument(
        "--config",
        help="Path to a JSON config file (defaults to ./config.local.json).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    config = AppConfig.load(args.config)
    if args.host:
        config.host = args.host
    if args.port:
        config.port = args.port
    if args.imperial:
        config.use_metric = False
    return Application(config).run()


if __name__ == "__main__":
    raise SystemExit(main())
