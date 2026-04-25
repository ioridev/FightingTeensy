#!/usr/bin/env python3
"""Local Web UI server for FightingTeensy configuration firmware."""

from __future__ import annotations

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional

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

    return [
        {
            "device": port.device,
            "description": port.description,
            "hwid": port.hwid,
        }
        for port in list_ports.comports()
    ]


class WebConfigApp:
    def __init__(
        self,
        default_port: Optional[str] = None,
        baud: int = 115200,
        device_factory: DeviceFactory = FightingTeensySerial,
        port_lister: PortLister = default_port_lister,
    ) -> None:
        self.default_port = default_port
        self.baud = baud
        self._device_factory = device_factory
        self._port_lister = port_lister

    def ports(self) -> JsonDict:
        return {"ok": True, "ports": list(self._port_lister())}

    def ping(self, payload: JsonDict) -> JsonDict:
        return self._safe_command(payload, "PING")

    def settings(self, payload: JsonDict) -> JsonDict:
        return self._safe_command(payload, "GET")

    def sample(self, payload: JsonDict) -> JsonDict:
        return self._safe_command(payload, "SAMPLE")

    def save(self, payload: JsonDict) -> JsonDict:
        return self._safe_command(payload, "SAVE")

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
            "/api/calibrate": self.calibrate,
            "/api/set": self.set_values,
            "/api/save": self.save,
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
