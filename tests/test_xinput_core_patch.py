import unittest

from tools.teensy_xinput_core_patch import (
    patch_usb_c,
    patch_usb_desc_c,
    patch_usb_desc_h,
    patch_usb_inst_cpp,
    patch_usb_serial_h,
    patch_wprogram_h,
)


class XInputCorePatchTests(unittest.TestCase):
    def test_usb_desc_h_inserts_xinput_branch_before_descriptor_list(self):
        base = "#elif defined(USB_EVERYTHING)\n  #define NUM_ENDPOINTS 15\n\n#endif\n\n#ifdef USB_DESC_LIST_DEFINE\n"
        donor = "#elif defined(USB_XINPUT)\n  #define VENDOR_ID 0x045e\n  #define XINPUT_INTERFACE 0\n\n#if defined(NUM_ENDPOINTS)\n"

        patched = patch_usb_desc_h(base, donor)

        self.assertIn("#elif defined(USB_XINPUT)", patched)
        self.assertLess(patched.index("#elif defined(USB_XINPUT)"), patched.index("#endif\n\n#ifdef USB_DESC_LIST_DEFINE"))

    def test_usb_c_adds_xinput_without_removing_existing_core_includes(self):
        base = (
            '#include "usb_mtp.h"\n'
            '#include "core_pins.h" // for delay()\n'
            "case 0x0900: // SET_CONFIGURATION\n"
            "\t\t// configure all other endpoints\n"
            "\t\t#if defined(ENDPOINT2_CONFIG)\n"
            "\t\t#if defined(MTP_INTERFACE)\n"
            "\t\tusb_mtp_configure();\n"
            "\t\t#endif\n"
            "\t\t#if defined(EXPERIMENTAL_INTERFACE)\n"
            "\t\t#endif\n"
            "static void endpoint0_complete(void)\n"
            "{\n\tsetup_t setup;\n}\n"
            "\nstatic void usb_endpoint_config(endpoint_t *qh, uint32_t config, void (*callback)(transfer_t *))\n"
            "{\n}\n"
            "void usb_config_rx(uint32_t ep, uint32_t packet_size, int do_zlp, void (*cb)(transfer_t *))\n"
            "{\n\tif (ep < 2 || ep > NUM_ENDPOINTS) return;\n}\n"
            "void usb_receive(uint32_t endpoint_number, transfer_t *transfer)\n"
            "{\n\tif (endpoint_number < 2 || endpoint_number > NUM_ENDPOINTS) return;\n}\n"
            "void usb_transmit(uint32_t endpoint_number, transfer_t *transfer)\n"
            "{\n\tif (endpoint_number < 2 || endpoint_number > NUM_ENDPOINTS) return;\n}\n"
        )

        patched = patch_usb_c(base)

        self.assertIn('#include "usb_xinput.h"', patched)
        self.assertIn("USB1_ENDPTCTRL1 = ENDPOINT1_CONFIG;", patched)
        self.assertIn("usb_xinput_configure();", patched)
        self.assertIn("(void) endpoint0_buffer;", patched)
        self.assertIn("#if defined(XINPUT_INTERFACE)\n\tif (ep < 1 || ep > NUM_ENDPOINTS) return;", patched)
        self.assertIn(
            "#if defined(XINPUT_INTERFACE)\n\tif (endpoint_number < 1 || endpoint_number > NUM_ENDPOINTS) return;",
            patched,
        )

    def test_wprogram_and_usb_inst_expose_xinput_symbols(self):
        self.assertIn(
            '#include "usb_xinput.h"',
            patch_wprogram_h('#include "usb_desc.h"\n#include "MTP_Teensy.h"\n'),
        )
        self.assertIn(
            "usb_serial_class Serial;",
            patch_usb_inst_cpp("#ifdef USB_DISABLED\nusb_serial_class Serial;\n#endif\n"),
        )

    def test_usb_serial_h_adds_xinput_serial_stub_only(self):
        base = (
            "#include <stdint.h>\n"
            "#if (defined(CDC_STATUS_INTERFACE) && defined(CDC_DATA_INTERFACE)) || defined(USB_DISABLED)\n"
            "#if !defined(USB_DISABLED)\n"
            "extern usb_serial_class Serial;\n"
        )

        patched = patch_usb_serial_h(base)

        self.assertIn("|| defined(USB_XINPUT)", patched)
        self.assertIn("#if !(defined(USB_DISABLED) || defined(USB_XINPUT))", patched)

    def test_usb_serial_h_declares_serial_event_for_xinput_stub(self):
        base = (
            "#include <stdint.h>\n"
            "#if (defined(CDC_STATUS_INTERFACE) && defined(CDC_DATA_INTERFACE)) || defined(USB_DISABLED)\n"
            "#if !defined(USB_DISABLED)\n"
            "#else  // !defined(USB_DISABLED)\n"
            "extern usb_serial_class Serial;\n"
            "#endif // __cplusplus\n"
        )

        patched = patch_usb_serial_h(base)

        self.assertIn('extern "C" void serialEvent(void) __attribute__((weak));', patched)

    def test_usb_desc_c_inserts_security_string_outside_config_arrays(self):
        base = (
            "#define CONFIG_DESC_SIZE\t\tEXPERIMENTAL_INTERFACE_DESC_POS+EXPERIMENTAL_INTERFACE_DESC_SIZE\n"
            "PROGMEM const uint8_t usb_config_descriptor_480[CONFIG_DESC_SIZE] = {\n"
            "#endif // EXPERIMENTAL_INTERFACE\n"
            "};\n"
            "PROGMEM const uint8_t usb_config_descriptor_12[CONFIG_DESC_SIZE] = {\n"
            "#endif // EXPERIMENTAL_INTERFACE\n"
            "};\n"
            "struct usb_string_descriptor_struct usb_string_serial_number_default = {\n};\n"
            "#ifdef MTP_INTERFACE\nPROGMEM const struct usb_string_descriptor_struct usb_string_mtp = {\n};\n#endif\n"
            "const usb_descriptor_list_t usb_descriptor_list[] = {\n"
            "\t{0, 0, NULL, 0}\n"
            "};\n"
        )
        donor = (
            "usb_config_descriptor_480\n#ifdef XINPUT_INTERFACE\n480 descriptor\n#endif // XINPUT_INTERFACE\n"
            "usb_config_descriptor_12\n#ifdef XINPUT_INTERFACE\n12 descriptor\n#endif // XINPUT_INTERFACE\n"
            "#ifdef XINPUT_INTERFACE\nstruct usb_string_descriptor_struct usb_string_xinput_security_descriptor = {\n};\n#endif\n"
        )

        patched = patch_usb_desc_c(base, donor)

        self.assertIn("#ifndef CONFIG_DESC_SIZE", patched)
        self.assertLess(
            patched.index("struct usb_string_descriptor_struct usb_string_serial_number_default"),
            patched.index("usb_string_xinput_security_descriptor"),
        )
        self.assertLess(
            patched.index("usb_string_xinput_security_descriptor"),
            patched.index("PROGMEM const struct usb_string_descriptor_struct usb_string_mtp"),
        )


if __name__ == "__main__":
    unittest.main()
