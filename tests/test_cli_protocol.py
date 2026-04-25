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


if __name__ == "__main__":
    unittest.main()

