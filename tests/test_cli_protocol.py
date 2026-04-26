import unittest

from tools.fighting_teensy_cli import command_for_action, parse_response, response_to_table


class ProtocolParsingTests(unittest.TestCase):
    def test_parse_settings_response_fields(self):
        response = parse_response(
            "SETTINGS socd=0 rate_khz=8 key0_rest=512 key0_press=80 key0_rapid=28"
        )

        self.assertEqual(response.kind, "SETTINGS")
        self.assertEqual(response.fields["socd"], "0")
        self.assertEqual(response.fields["rate_khz"], "8")
        self.assertEqual(response.fields["key0_rest"], "512")
        self.assertEqual(response.fields["key0_press"], "80")
        self.assertEqual(response.fields["key0_rapid"], "28")

    def test_parse_sample_response_with_pressed_state(self):
        response = parse_response("SAMPLE key0_raw=510 key0_travel=42 key0_pressed=1")

        self.assertEqual(response.kind, "SAMPLE")
        self.assertEqual(response.fields["key0_raw"], "510")
        self.assertEqual(response.fields["key0_travel"], "42")
        self.assertEqual(response.fields["key0_pressed"], "1")

    def test_parse_ok_response_without_fields(self):
        response = parse_response("OK saved")

        self.assertEqual(response.kind, "OK")
        self.assertEqual(response.fields, {})
        self.assertEqual(response_to_table(response), "OK saved")

    def test_empty_response_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_response("")

    def test_action_to_firmware_command(self):
        self.assertEqual(command_for_action("ping"), "PING")
        self.assertEqual(command_for_action("cal-rest"), "CAL REST")
        self.assertEqual(command_for_action("reset"), "RESET")
        self.assertEqual(command_for_action("bootloader"), "BOOTLOADER")
        self.assertEqual(command_for_action("pins"), "PINS")
        self.assertEqual(command_for_action("buttons"), "BUTTONS")

    def test_set_command_builds_key_value_protocol(self):
        command = command_for_action(
            "set",
            socd="up",
            rate_khz=8,
            key="left",
            press=72,
            release=40,
            rapid=24,
            active_low=1,
        )

        self.assertEqual(
            command,
            "SET socd=1 rate_khz=8 key2_press=72 key2_release=40 key2_rapid=24 key2_active_low=1",
        )

    def test_set_command_builds_button_pin_protocol(self):
        command = command_for_action("set", button="start", pin=6)

        self.assertEqual(command, "SET btn_start_pin=6")

    def test_set_command_builds_multiple_button_pins(self):
        command = command_for_action(
            "set",
            button_pins={
                "a": 11,
                "b": 12,
                "start": 6,
            },
        )

        self.assertEqual(command, "SET btn_a_pin=11 btn_b_pin=12 btn_start_pin=6")

    def test_set_command_rejects_unknown_button(self):
        with self.assertRaises(ValueError):
            command_for_action("set", button="turbo", pin=22)

    def test_cal_key_command_builds_named_key_protocol(self):
        self.assertEqual(
            command_for_action("cal-key", key="right", point="bottom"),
            "CAL KEY 3 BOTTOM",
        )

    def test_set_requires_at_least_one_setting(self):
        with self.assertRaises(ValueError):
            command_for_action("set")

    def test_set_rejects_unknown_key(self):
        with self.assertRaises(ValueError):
            command_for_action("set", key="north", press=80)

    def test_cal_key_rejects_unknown_point(self):
        with self.assertRaises(ValueError):
            command_for_action("cal-key", key="up", point="middle")


if __name__ == "__main__":
    unittest.main()
