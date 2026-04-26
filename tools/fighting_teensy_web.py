#!/usr/bin/env python3
"""Local Web UI server for FightingTeensy configuration firmware."""

from __future__ import annotations

import argparse
import json
import mimetypes
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional, Sequence

try:
    from .fighting_teensy_cli import (
        DeviceResponse,
        FightingTeensySerial,
        command_for_action,
    )
except ImportError:
    from fighting_teensy_cli import (
        DeviceResponse,
        FightingTeensySerial,
        command_for_action,
    )


JsonDict = Dict[str, Any]
DeviceFactory = Callable[[str, int], Any]
PortLister = Callable[[], Iterable[JsonDict]]
BootloaderDetector = Callable[[], bool]
CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


def response_to_json(response: DeviceResponse) -> JsonDict:
    return {
        "kind": response.kind,
        "fields": response.fields,
        "text": response.text,
    }


def default_port_lister() -> Iterable[JsonDict]:
    try:
        from serial.tools import list_ports  # type: ignore
    except ImportError:
        return []

    ports = [
        {
            "device": port.device,
            "description": port.description,
            "hwid": port.hwid,
        }
        for port in list_ports.comports()
    ]
    return sorted(
        ports,
        key=lambda port: (
            0 if "VID:PID=16C0:0483" in str(port.get("hwid", "")).upper() else 1,
            str(port.get("device", "")),
        ),
    )


def default_bootloader_detector() -> bool:
    import os

    if os.name != "nt":
        return False

    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "Get-CimInstance Win32_PnPEntity | "
            "Where-Object { $_.DeviceID -match 'VID_16C0&PID_0478' } | "
            "Select-Object -First 1 -ExpandProperty DeviceID"
        ),
    ]
    try:
        result = subprocess.run(
            command,
            timeout=4,
            text=True,
            capture_output=True,
        )
    except Exception:
        return False
    return result.returncode == 0 and "VID_16C0&PID_0478" in (result.stdout or "").upper()


class FirmwareFlasher:
    TARGETS = {
        "config": "teensy40_config_serial",
        "xinput": "teensy40_xinput",
    }

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        baud: int = 115200,
        runner: CommandRunner = subprocess.run,
        device_factory: DeviceFactory = FightingTeensySerial,
    ) -> None:
        self.project_dir = project_dir or Path(__file__).resolve().parents[1]
        self.baud = baud
        self._runner = runner
        self._device_factory = device_factory

    def flash(self, target: str, port: Optional[str] = None) -> JsonDict:
        if target not in self.TARGETS:
            raise ValueError(f"unknown firmware target: {target}")

        env = self.TARGETS[target]
        log = []
        log.append(self._run(["pio", "run", "-e", env], timeout=120))

        if port:
            self._request_bootloader(port)
            time.sleep(0.8)

        firmware = self.project_dir / ".pio" / "build" / env / "firmware.hex"
        log.append(
            self._run(
                [
                    str(self._loader_path()),
                    "--mcu=TEENSY40",
                    "-w",
                    "-v",
                    str(firmware),
                ],
                timeout=60,
            )
        )
        return {"target": target, "environment": env, "log": "\n".join(log)}

    def _request_bootloader(self, port: str) -> None:
        device = self._device_factory(port, self.baud)
        try:
            device.command(command_for_action("bootloader"))
        except Exception:
            # The board may drop USB before the response reaches the host.
            pass
        finally:
            try:
                device.close()
            except Exception:
                pass

    def _run(self, command: Sequence[str], timeout: int) -> str:
        result = self._runner(
            list(command),
            cwd=self.project_dir,
            timeout=timeout,
            text=True,
            capture_output=True,
        )
        output = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0:
            raise RuntimeError(output.strip() or f"command failed: {' '.join(command)}")
        return output.strip()

    @staticmethod
    def _loader_path() -> Path:
        import os

        suffix = "teensy_loader_cli.exe" if os.name == "nt" else "teensy_loader_cli"
        return Path.home() / ".platformio" / "packages" / "tool-teensy" / suffix


class WebConfigApp:
    def __init__(
        self,
        default_port: Optional[str] = None,
        baud: int = 115200,
        device_factory: DeviceFactory = FightingTeensySerial,
        port_lister: PortLister = default_port_lister,
        bootloader_detector: BootloaderDetector = default_bootloader_detector,
        flasher: Optional[FirmwareFlasher] = None,
    ) -> None:
        self.default_port = default_port
        self.baud = baud
        self._device_factory = device_factory
        self._port_lister = port_lister
        self._bootloader_detector = bootloader_detector
        self._flasher = flasher or FirmwareFlasher(baud=baud, device_factory=device_factory)
        self._serial_lock = threading.Lock()

    def ports(self) -> JsonDict:
        return {
            "ok": True,
            "ports": list(self._port_lister()),
            "bootloader": {
                "present": self._bootloader_detector(),
                "vid_pid": "16C0:0478",
                "name": "Teensy HalfKay",
            },
        }

    def ping(self, payload: JsonDict) -> JsonDict:
        return self._safe_command(payload, "PING")

    def settings(self, payload: JsonDict) -> JsonDict:
        return self._safe_command(payload, "GET")

    def sample(self, payload: JsonDict) -> JsonDict:
        return self._safe_command(payload, "SAMPLE")

    def pins(self, payload: JsonDict) -> JsonDict:
        return self._safe_command(payload, command_for_action("pins"))

    def buttons(self, payload: JsonDict) -> JsonDict:
        return self._safe_command(payload, command_for_action("buttons"))

    def save(self, payload: JsonDict) -> JsonDict:
        return self._safe_command(payload, "SAVE")

    def bootloader(self, payload: JsonDict) -> JsonDict:
        return self._safe_command(payload, command_for_action("bootloader"))

    def flash(self, payload: JsonDict) -> JsonDict:
        try:
            target = str(payload.get("target", ""))
            port = str(payload.get("port") or self.default_port or "") or None
            return {"ok": True, "flash": self._flasher.flash(target, port=port)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def calibrate(self, payload: JsonDict) -> JsonDict:
        point = str(payload.get("point", "bottom")).lower()
        if point == "rest" and "key" not in payload:
            return self._safe_command(payload, command_for_action("cal-rest"))
        return self._safe_command(
            payload,
            command_for_action("cal-key", key=str(payload.get("key", "")), point=point),
        )

    def set_values(self, payload: JsonDict) -> JsonDict:
        options: JsonDict = {
            "socd": payload.get("socd"),
            "rate_khz": self._optional_int(payload, "rate_khz"),
            "key": payload.get("key"),
            "button": payload.get("button"),
            "pin": self._optional_int(payload, "pin"),
            "button_pins": self._optional_int_map(payload, "button_pins"),
            "rest": self._optional_int(payload, "rest"),
            "bottom": self._optional_int(payload, "bottom"),
            "press": self._optional_int(payload, "press"),
            "release": self._optional_int(payload, "release"),
            "rapid": self._optional_int(payload, "rapid"),
            "active_low": self._optional_int(payload, "active_low"),
        }
        return self._safe_command(payload, command_for_action("set", **options))

    def route(self, method: str, path: str, payload: JsonDict) -> JsonDict:
        if method == "GET" and path == "/api/ports":
            return self.ports()
        if method != "POST":
            return {"ok": False, "error": "method not allowed"}

        routes = {
            "/api/ping": self.ping,
            "/api/settings": self.settings,
            "/api/sample": self.sample,
            "/api/pins": self.pins,
            "/api/buttons": self.buttons,
            "/api/calibrate": self.calibrate,
            "/api/set": self.set_values,
            "/api/save": self.save,
            "/api/bootloader": self.bootloader,
            "/api/flash": self.flash,
        }
        handler = routes.get(path)
        if handler is None:
            return {"ok": False, "error": "unknown endpoint"}
        return handler(payload)

    def _safe_command(self, payload: JsonDict, command: str) -> JsonDict:
        try:
            response = self._command(payload, command)
            return {"ok": True, "response": response_to_json(response)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _command(self, payload: JsonDict, command: str) -> DeviceResponse:
        port = str(payload.get("port") or self.default_port or "")
        if not port:
            raise ValueError("serial port is required")

        with self._serial_lock:
            device = self._device_factory(port, self.baud)
            try:
                return device.command(command)
            finally:
                device.close()

    @staticmethod
    def _optional_int(payload: JsonDict, name: str) -> Optional[int]:
        value = payload.get(name)
        if value is None or value == "":
            return None
        return int(value)

    @staticmethod
    def _optional_int_map(payload: JsonDict, name: str) -> Optional[Dict[str, int]]:
        value = payload.get(name)
        if value is None:
            return None
        if not isinstance(value, dict):
            raise ValueError(f"{name} must be an object")
        return {str(key): int(item) for key, item in value.items()}


def create_server(
    host: str,
    port: int,
    app: WebConfigApp,
    static_dir: Optional[Path] = None,
) -> ThreadingHTTPServer:
    assets = static_dir or Path(__file__).with_name("web_config")

    class Handler(BaseHTTPRequestHandler):
        server_version = "FightingTeensyWeb/0.1"

        def do_GET(self) -> None:
            if self.path == "/api/ports":
                self._write_json(app.route("GET", self.path, {}))
                return
            self._serve_static()

        def do_POST(self) -> None:
            payload = self._read_json()
            self._write_json(app.route("POST", self.path, payload))

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _read_json(self) -> JsonDict:
            length = int(self.headers.get("Content-Length", "0"))
            if length == 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            return json.loads(raw)

        def _write_json(self, payload: JsonDict) -> None:
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _serve_static(self) -> None:
            relative = "index.html" if self.path in ("/", "") else self.path.lstrip("/")
            target = (assets / relative).resolve()
            if assets.resolve() not in target.parents and target != assets.resolve():
                self.send_error(404)
                return
            if not target.is_file():
                self.send_error(404)
                return

            content = target.read_bytes()
            content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

    return ThreadingHTTPServer((host, port), Handler)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the FightingTeensy local Web UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--device", help="Default serial port, for example COM3")
    parser.add_argument("--baud", type=int, default=115200)
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    app = WebConfigApp(default_port=args.device, baud=args.baud)
    server = create_server(args.host, args.port, app)
    print(f"FightingTeensy Web Config: http://{args.host}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
