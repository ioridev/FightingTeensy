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


KEY_INDEX = {
    "up": 0,
    "down": 1,
    "left": 2,
    "right": 3,
    "0": 0,
    "1": 1,
    "2": 2,
    "3": 3,
}

SOCD_MODE = {
    "neutral": 0,
    "up": 1,
    "up-priority": 1,
}

BUTTON_INDEX = {
    "a": "a",
    "b": "b",
    "x": "x",
    "y": "y",
    "lb": "lb",
    "rb": "rb",
    "back": "back",
    "start": "start",
    "l3": "l3",
    "r3": "r3",
    "logo": "logo",
    "home": "logo",
    "xbox": "logo",
    "lt": "lt",
    "trigger_l": "lt",
    "rt": "rt",
    "trigger_r": "rt",
}


def _key_index(value: str) -> int:
    key = value.lower()
    if key not in KEY_INDEX:
        raise ValueError(f"unknown key: {value}")
    return KEY_INDEX[key]


def _socd_mode(value: str) -> int:
    mode = value.lower()
    if mode not in SOCD_MODE:
        raise ValueError(f"unknown SOCD mode: {value}")
    return SOCD_MODE[mode]


def _button_name(value: str) -> str:
    button = value.lower()
    if button not in BUTTON_INDEX:
        raise ValueError(f"unknown button: {value}")
    return BUTTON_INDEX[button]


def _append_optional(tokens: list[str], name: str, value: object) -> None:
    if value is not None:
        tokens.append(f"{name}={value}")


def command_for_action(action: str, **options: object) -> str:
    commands = {
        "ping": "PING",
        "get": "GET",
        "sample": "SAMPLE",
        "pins": "PINS",
        "buttons": "BUTTONS",
        "cal-rest": "CAL REST",
        "save": "SAVE",
        "reset": "RESET",
        "bootloader": "BOOTLOADER",
    }
    if action in commands:
        return commands[action]

    if action == "set":
        tokens = ["SET"]
        socd = options.get("socd")
        if socd is not None:
            tokens.append(f"socd={_socd_mode(str(socd))}")
        _append_optional(tokens, "rate_khz", options.get("rate_khz"))

        button = options.get("button")
        pin = options.get("pin")
        if button is not None or pin is not None:
            if button is None or pin is None:
                raise ValueError("button pin setting requires button and pin")
            tokens.append(f"btn_{_button_name(str(button))}_pin={pin}")

        button_pins = options.get("button_pins")
        if button_pins is not None:
            if not isinstance(button_pins, dict):
                raise ValueError("button_pins must be a dict")
            for button_name, button_pin in button_pins.items():
                tokens.append(f"btn_{_button_name(str(button_name))}_pin={button_pin}")

        key = options.get("key")
        if key is not None:
            index = _key_index(str(key))
            _append_optional(tokens, f"key{index}_rest", options.get("rest"))
            _append_optional(tokens, f"key{index}_bottom", options.get("bottom"))
            _append_optional(tokens, f"key{index}_press", options.get("press"))
            _append_optional(tokens, f"key{index}_release", options.get("release"))
            _append_optional(tokens, f"key{index}_rapid", options.get("rapid"))
            _append_optional(tokens, f"key{index}_active_low", options.get("active_low"))

        if len(tokens) == 1:
            raise ValueError("set requires at least one setting")
        return " ".join(tokens)

    if action == "cal-key":
        key = options.get("key")
        point = options.get("point")
        if key is None or point is None:
            raise ValueError("cal-key requires key and point")
        point_text = str(point).upper()
        if point_text not in ("REST", "BOTTOM"):
            raise ValueError(f"unknown calibration point: {point}")
        return f"CAL KEY {_key_index(str(key))} {point_text}"

    raise KeyError(action)


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
    for action in ("ping", "get", "sample", "pins", "buttons", "cal-rest", "save", "reset", "bootloader"):
        subparsers.add_parser(action)

    set_parser = subparsers.add_parser("set")
    set_parser.add_argument("--socd", choices=sorted(SOCD_MODE), help="SOCD mode")
    set_parser.add_argument("--rate-khz", type=int, choices=(1, 2, 4, 8))
    set_parser.add_argument("--button", choices=sorted(BUTTON_INDEX))
    set_parser.add_argument("--pin", type=int)
    set_parser.add_argument("--key", choices=sorted(KEY_INDEX))
    set_parser.add_argument("--rest", type=int)
    set_parser.add_argument("--bottom", type=int)
    set_parser.add_argument("--press", type=int)
    set_parser.add_argument("--release", type=int)
    set_parser.add_argument("--rapid", type=int)
    set_parser.add_argument("--active-low", type=int, choices=(0, 1))

    cal_key_parser = subparsers.add_parser("cal-key")
    cal_key_parser.add_argument("--key", required=True, choices=sorted(KEY_INDEX))
    cal_key_parser.add_argument("--point", required=True, choices=("rest", "bottom"))

    monitor_parser = subparsers.add_parser("monitor")
    monitor_parser.add_argument("--interval", type=float, default=0.1)
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.action == "monitor":
            return monitor(args.port, args.baud, args.interval)
        if args.action == "set":
            device = FightingTeensySerial(port=args.port, baud=args.baud)
            try:
                response = device.command(
                    command_for_action(
                        "set",
                        socd=args.socd,
                        rate_khz=args.rate_khz,
                        button=args.button,
                        pin=args.pin,
                        key=args.key,
                        rest=args.rest,
                        bottom=args.bottom,
                        press=args.press,
                        release=args.release,
                        rapid=args.rapid,
                        active_low=args.active_low,
                    )
                )
                print(response_to_table(response))
                return 0
            finally:
                device.close()
        if args.action == "cal-key":
            device = FightingTeensySerial(port=args.port, baud=args.baud)
            try:
                response = device.command(
                    command_for_action("cal-key", key=args.key, point=args.point)
                )
                print(response_to_table(response))
                return 0
            finally:
                device.close()
        return run_once(args.port, args.action, args.baud)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
