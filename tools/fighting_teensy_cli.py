#!/usr/bin/env python3
"""Small host tool for FightingTeensy configuration firmware."""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from typing import Dict, Iterable, Optional


@dataclass(frozen=True)
class DeviceResponse:
    kind: str
    fields: Dict[str, str]
    text: str


def parse_response(line: str) -> DeviceResponse:
    text = line.strip()
    if not text:
        raise ValueError("empty response")

    parts = text.split()
    kind = parts[0]
    fields: Dict[str, str] = {}
    for token in parts[1:]:
        if "=" in token:
            key, value = token.split("=", 1)
            fields[key] = value

    return DeviceResponse(kind=kind, fields=fields, text=text)


def response_to_table(response: DeviceResponse) -> str:
    if not response.fields:
        return response.text

    width = max(len(key) for key in response.fields)
    rows = [response.kind]
    for key in sorted(response.fields):
        rows.append(f"  {key.ljust(width)}  {response.fields[key]}")
    return "\n".join(rows)


class FightingTeensySerial:
    def __init__(self, port: str, baud: int = 115200, timeout: float = 2.0) -> None:
        try:
            import serial  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "pyserial is required. Install with: python -m pip install pyserial"
            ) from exc

        self._serial = serial.Serial(port=port, baudrate=baud, timeout=timeout)
        time.sleep(0.2)

    def close(self) -> None:
        self._serial.close()

    def command(self, command: str) -> DeviceResponse:
        self._serial.reset_input_buffer()
        self._serial.write((command.strip() + "\n").encode("ascii"))
        self._serial.flush()

        deadline = time.time() + 2.0
        while time.time() < deadline:
            line = self._serial.readline().decode("ascii", errors="replace").strip()
            if not line:
                continue
            if line.startswith("OK FightingTeensy config"):
                continue
            return parse_response(line)

        raise TimeoutError(f"no response for command: {command}")


def command_for_action(action: str) -> str:
    commands = {
        "ping": "PING",
        "get": "GET",
        "sample": "SAMPLE",
        "cal-rest": "CAL REST",
        "save": "SAVE",
        "reset": "RESET",
    }
    return commands[action]


def run_once(port: str, action: str, baud: int) -> int:
    device = FightingTeensySerial(port=port, baud=baud)
    try:
        response = device.command(command_for_action(action))
        print(response_to_table(response))
        return 0
    finally:
        device.close()


def monitor(port: str, baud: int, interval: float) -> int:
    device = FightingTeensySerial(port=port, baud=baud)
    try:
        while True:
            response = device.command("SAMPLE")
            print(response_to_table(response))
            print()
            time.sleep(interval)
    except KeyboardInterrupt:
        return 0
    finally:
        device.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Configure a FightingTeensy running the serial config firmware."
    )
    parser.add_argument("--port", required=True, help="Serial port, for example COM7")
    parser.add_argument("--baud", type=int, default=115200)

    subparsers = parser.add_subparsers(dest="action", required=True)
    for action in ("ping", "get", "sample", "cal-rest", "save", "reset"):
        subparsers.add_parser(action)

    monitor_parser = subparsers.add_parser("monitor")
    monitor_parser.add_argument("--interval", type=float, default=0.1)
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
      if args.action == "monitor":
          return monitor(args.port, args.baud, args.interval)
      return run_once(args.port, args.action, args.baud)
    except Exception as exc:
      print(f"error: {exc}", file=sys.stderr)
      return 1


if __name__ == "__main__":
    raise SystemExit(main())

