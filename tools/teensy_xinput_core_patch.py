from __future__ import annotations

def _insert_once(text: str, marker: str, insertion: str) -> str:
    if insertion.strip() in text:
        return text
    if marker not in text:
        raise ValueError(f"marker not found: {marker!r}")
    return text.replace(marker, insertion + marker, 1)


def _extract_between(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index) + len(end)
    return text[start_index:end_index]


def _extract_xinput_usb_desc_h_block(donor: str) -> str:
    start = donor.index("#elif defined(USB_XINPUT)")
    end = donor.index("\n#if defined(NUM_ENDPOINTS)", start)
    return donor[start:end] + "\n"


def patch_usb_desc_h(base: str, donor: str) -> str:
    block = _extract_xinput_usb_desc_h_block(donor)
    return _insert_once(base, "\n#endif\n\n#ifdef USB_DESC_LIST_DEFINE", "\n" + block)


def patch_wprogram_h(base: str) -> str:
    marker = '#include "MTP_Teensy.h"\n'
    if marker not in base:
        marker = '#include "usb_desc.h"\n'
    return _insert_once(base, marker, '#include "usb_xinput.h"\n')


def patch_usb_inst_cpp(base: str) -> str:
    block = "#ifdef USB_XINPUT\nusb_serial_class Serial;\n#endif\n\n"
    return _insert_once(base, "#ifdef USB_DISABLED\n", block)


def patch_usb_serial_h(base: str) -> str:
    text = _insert_once(
        base,
        "#include <stdint.h>\n",
        '#ifdef __cplusplus\nextern "C" void serialEvent(void) __attribute__((weak));\n#endif\n',
    )
    text = text.replace(
        "#if (defined(CDC_STATUS_INTERFACE) && defined(CDC_DATA_INTERFACE)) || defined(USB_DISABLED)",
        "#if (defined(CDC_STATUS_INTERFACE) && defined(CDC_DATA_INTERFACE)) || defined(USB_DISABLED) || defined(USB_XINPUT)",
        1,
    )
    text = text.replace(
        "#if !defined(USB_DISABLED)",
        "#if !(defined(USB_DISABLED) || defined(USB_XINPUT))",
        1,
    )
    return text


def _patch_usb_config_endpoint_guard(text: str) -> str:
    old = "\tif (ep < 2 || ep > NUM_ENDPOINTS) return;"
    new = (
        "#if defined(XINPUT_INTERFACE)\n"
        "\tif (ep < 1 || ep > NUM_ENDPOINTS) return;\n"
        "#else\n"
        "\tif (ep < 2 || ep > NUM_ENDPOINTS) return;\n"
        "#endif"
    )
    return text.replace(old, new)


def _patch_xinput_endpoint0_warning_suppression(text: str) -> str:
    block = (
        "#ifdef XINPUT_INTERFACE\n"
        "\t// Suppress XInput-only unused warnings when CDC/audio/MTP handlers are absent.\n"
        "\t(void) setup.wIndex;\n"
        "\t(void) endpoint0_buffer;\n"
        "#endif\n"
    )
    return _insert_once(text, "}\n\nstatic void usb_endpoint_config", block)


def patch_usb_c(base: str) -> str:
    text = _insert_once(base, '#include "usb_mtp.h"\n', '#include "usb_xinput.h"\n')
    text = _insert_once(
        text,
        "\t\t#if defined(ENDPOINT2_CONFIG)\n",
        "\t\t#if defined(ENDPOINT1_CONFIG)\n"
        "\t\tUSB1_ENDPTCTRL1 = ENDPOINT1_CONFIG;\n"
        "\t\t#endif\n",
    )
    text = _insert_once(
        text,
        "\t\t#if defined(EXPERIMENTAL_INTERFACE)\n",
        "\t\t#if defined(XINPUT_INTERFACE)\n"
        "\t\tusb_xinput_configure();\n"
        "\t\t#endif\n",
    )
    text = _patch_usb_config_endpoint_guard(text)
    return _patch_xinput_endpoint0_warning_suppression(text)


def _extract_xinput_descriptor_block(donor: str, descriptor_name: str) -> str:
    descriptor_start = donor.index(f"usb_config_descriptor_{descriptor_name}")
    block_start = donor.index("#ifdef XINPUT_INTERFACE", descriptor_start)
    block_end = donor.index("#endif // XINPUT_INTERFACE", block_start)
    return donor[block_start:block_end + len("#endif // XINPUT_INTERFACE")] + "\n"


def _patch_config_desc_size(text: str) -> str:
    old = "#define CONFIG_DESC_SIZE\t\tEXPERIMENTAL_INTERFACE_DESC_POS+EXPERIMENTAL_INTERFACE_DESC_SIZE"
    new = "#ifndef CONFIG_DESC_SIZE\n" + old + "\n#endif"
    return text.replace(old, new, 1)


def _insert_xinput_descriptor(text: str, donor: str, descriptor_name: str) -> str:
    block = _extract_xinput_descriptor_block(donor, descriptor_name)
    if block.strip() in text:
        return text

    start = text.index(f"usb_config_descriptor_{descriptor_name}")
    marker_index = text.index("#endif // EXPERIMENTAL_INTERFACE", start)
    close_index = text.index("\n};", marker_index)
    return text[: close_index + 1] + "\n" + block + text[close_index + 1 :]


def _patch_xinput_string_descriptor(text: str, donor: str) -> str:
    block = _extract_between(
        donor,
        "#ifdef XINPUT_INTERFACE\nstruct usb_string_descriptor_struct usb_string_xinput_security_descriptor",
        "#endif",
    )
    marker = "#ifdef MTP_INTERFACE\nPROGMEM const struct usb_string_descriptor_struct usb_string_mtp"
    return _insert_once(text, marker, block + "\n")


def _patch_xinput_descriptor_list_entry(text: str) -> str:
    block = (
        "#ifdef XINPUT_INTERFACE\n"
        '        {0x0304, 0x0409, (const uint8_t *)&usb_string_xinput_security_descriptor, 0},\n'
        "#endif\n"
    )
    return _insert_once(text, "\t{0, 0, NULL, 0}\n", block)


def patch_usb_desc_c(base: str, donor: str) -> str:
    text = _patch_config_desc_size(base)
    text = _insert_xinput_descriptor(text, donor, "480")
    text = _insert_xinput_descriptor(text, donor, "12")
    text = _patch_xinput_string_descriptor(text, donor)
    return _patch_xinput_descriptor_list_entry(text)


def patch_core_file(name: str, base: str, donor: str | None = None) -> str:
    if name == "usb.c":
        return patch_usb_c(base)
    if name == "usb_desc.c":
        if donor is None:
            raise ValueError("usb_desc.c patch requires donor text")
        return patch_usb_desc_c(base, donor)
    if name == "usb_desc.h":
        if donor is None:
            raise ValueError("usb_desc.h patch requires donor text")
        return patch_usb_desc_h(base, donor)
    if name == "WProgram.h":
        return patch_wprogram_h(base)
    if name == "usb_inst.cpp":
        return patch_usb_inst_cpp(base)
    if name == "usb_serial.h":
        return patch_usb_serial_h(base)
    return base
