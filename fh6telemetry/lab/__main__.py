"""Lab entry point: ``python -m fh6telemetry.lab``."""

from __future__ import annotations

import argparse
import sys

from ..config import AppConfig
from .app import LabApplication


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="fh6telemetry.lab",
        description="FH6Telemetry analysis lab — simulation and graphs.",
    )
    parser.add_argument("--imperial", action="store_true", help="Use mph for graphs.")
    parser.add_argument("--config", help="Path to JSON config override.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    config = AppConfig.load(args.config)
    if args.imperial:
        config.use_metric = False
    return LabApplication(config).run()


if __name__ == "__main__":
    raise SystemExit(main())
