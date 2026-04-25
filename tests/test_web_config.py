import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from tools.fighting_teensy_cli import parse_response
from tools.fighting_teensy_web import WebConfigApp, create_server


class FakeDevice:
    def __init__(self, responses):
        self.responses = list(responses)
        self.commands = []
        self.closed = False

    def command(self, command):
        self.commands.append(command)
        return parse_response(self.responses.pop(0))

    def close(self):
        self.closed = True


class WebConfigAppTests(unittest.TestCase):
    def test_calibrates_bottom_for_named_key(self):
        devices = []

        def factory(port, baud):
            device = FakeDevice(["OK key_calibrated key=3 point=bottom value=122"])
            devices.append((port, baud, device))
            return device

        app = WebConfigApp(default_port="COM3", device_factory=factory)

        result = app.calibrate({"key": "right"})

        self.assertEqual(result["ok"], True)
        self.assertEqual(result["response"]["fields"]["value"], "122")
        self.assertEqual(devices[0][0], "COM3")
        self.assertEqual(devices[0][2].commands, ["CAL KEY 3 BOTTOM"])
        self.assertEqual(devices[0][2].closed, True)

    def test_set_applies_threshold_values_and_active_low(self):
        devices = []

        def factory(port, baud):
            device = FakeDevice(["OK set"])
            devices.append(device)
            return device

        app = WebConfigApp(default_port="COM7", device_factory=factory)

        result = app.set_values(
            {
                "key": "left",
                "press": 70,
                "release": 35,
                "rapid": 18,
                "active_low": 1,
            }
        )

        self.assertEqual(result["ok"], True)
        self.assertEqual(
            devices[0].commands,
            ["SET key2_press=70 key2_release=35 key2_rapid=18 key2_active_low=1"],
        )

    def test_reports_serial_errors_as_json_safe_failures(self):
        def factory(port, baud):
            raise RuntimeError("port busy")

        app = WebConfigApp(default_port="COM3", device_factory=factory)

        result = app.ping({})

        self.assertEqual(result["ok"], False)
        self.assertEqual(result["error"], "port busy")

    def test_lists_ports_from_injected_lister(self):
        app = WebConfigApp(
            port_lister=lambda: [
                {"device": "COM3", "description": "USB Serial Device"},
                {"device": "COM9", "description": "Debug Port"},
            ]
        )

        self.assertEqual(app.ports()["ports"][0]["device"], "COM3")


class WebConfigHttpTests(unittest.TestCase):
    def test_http_api_returns_json(self):
        app = WebConfigApp(port_lister=lambda: [{"device": "COM3", "description": "USB"}])
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "index.html").write_text("<!doctype html><title>test</title>", encoding="utf-8")
            server = create_server("127.0.0.1", 0, app, static_dir=Path(tmp))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                port = server.server_address[1]
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ports", timeout=2) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["ports"][0]["device"], "COM3")


if __name__ == "__main__":
    unittest.main()
