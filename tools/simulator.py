"""Synthetic Forza telemetry generator for local testing.

Streams encoded 324-byte Horizon datagrams using the same :class:`ScenarioEngine`
that powers the Lab workbench, so overlay testing and offline analysis always
share identical physics.

Usage::

    python -m tools.simulator
    python -m tools.simulator --scenario circuit_lap --host 127.0.0.1 --port 5300
"""

from __future__ import annotations

import argparse
import socket
import time

from fh6telemetry.lab.scenarios import build_scenario_engine
from fh6telemetry.parser import encode


def _parse_args() -> argparse.Namespace:
    engine = build_scenario_engine()
    parser = argparse.ArgumentParser(description="Forza telemetry UDP simulator.")
    parser.add_argument("--host", default="127.0.0.1", help="Destination IP.")
    parser.add_argument("--port", type=int, default=5300, help="Destination UDP port.")
    parser.add_argument("--rate", type=float, default=60.0, help="Packets per second.")
    parser.add_argument(
        "--scenario",
        choices=engine.ids(),
        default="circuit_lap",
        help="Drive scenario to simulate (default: circuit_lap).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    engine = build_scenario_engine()
    engine.set_scenario(args.scenario)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dt = 1.0 / args.rate
    label = engine.scenario_name
    print(f"Scenario: {label}")
    print(f"Streaming to {args.host}:{args.port} at {args.rate:g} Hz")
    print("Press Ctrl+C to stop.")
    try:
        while True:
            frame = engine.step(dt)
            sock.sendto(encode(frame, size=324), (args.host, args.port))
            time.sleep(dt)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        sock.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
