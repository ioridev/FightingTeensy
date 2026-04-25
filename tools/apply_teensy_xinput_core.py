from pathlib import Path
import os
import shutil

Import("env")
from SCons.Script import COMMAND_LINE_TARGETS, Exit

from teensy_xinput_core_patch import patch_core_file


CORE_FILES = (
    "usb.c",
    "usb_desc.c",
    "usb_desc.h",
    "usb_inst.cpp",
    "usb_serial.h",
    "WProgram.h",
)

XINPUT_ONLY_FILES = (
    "usb_xinput.c",
    "usb_xinput.h",
)


def copy_if_changed(source: Path, destination: Path) -> bool:
    if destination.exists() and destination.read_bytes() == source.read_bytes():
        return False

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return True


def write_if_changed(destination: Path, content: str) -> bool:
    encoded = content.encode("utf-8")
    if destination.exists() and destination.read_bytes() == encoded:
        return False

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(encoded)
    return True


pio_env = env.subst("$PIOENV")
project_dir = Path(env.subst("$PROJECT_DIR"))
framework_dir = Path(env.PioPlatform().get_package_dir("framework-arduinoteensy"))
destination_dir = framework_dir / "cores" / "teensy4"
teensyduino_source_dir = project_dir / "third_party" / "Teensyduino_1.60" / "cores" / "teensy4"
arduino_xinput_source_dir = project_dir / "third_party" / "ArduinoXInput_Teensy" / "teensy" / "avr" / "cores" / "teensy4"

is_xinput_env = pio_env.startswith("teensy40_xinput")

if is_xinput_env:
    if "upload" in COMMAND_LINE_TARGETS and os.environ.get("FIGHTING_TEENSY_ALLOW_XINPUT_UPLOAD") != "1":
        print(
            f"Refusing to upload {pio_env} without "
            "FIGHTING_TEENSY_ALLOW_XINPUT_UPLOAD=1. "
            "Builds are allowed; flash teensy40_config_serial for recovery/config work."
        )
        Exit(1)

    files = CORE_FILES
    mode = "Teensyduino 1.60 + XInput overlay"
else:
    files = CORE_FILES
    mode = "Teensyduino 1.60"
    for name in XINPUT_ONLY_FILES:
        extra_file = destination_dir / name
        if extra_file.exists():
            extra_file.unlink()

changed = []
for name in files:
    source = teensyduino_source_dir / name
    destination = destination_dir / name
    if not source.exists():
        raise FileNotFoundError(source)

    if is_xinput_env:
        donor = None
        donor_path = arduino_xinput_source_dir / name
        if donor_path.exists():
            donor = donor_path.read_text(encoding="utf-8")
        content = patch_core_file(name, source.read_text(encoding="utf-8"), donor)
        file_changed = write_if_changed(destination, content)
    else:
        file_changed = copy_if_changed(source, destination)

    if file_changed:
        changed.append(name)

if is_xinput_env:
    for name in XINPUT_ONLY_FILES:
        source = arduino_xinput_source_dir / name
        destination = destination_dir / name
        if not source.exists():
            raise FileNotFoundError(source)
        if copy_if_changed(source, destination):
            changed.append(name)

if changed:
    print(f"Applied {mode} core files: " + ", ".join(changed))
