from pathlib import Path
import shutil

Import("env")


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


pio_env = env.subst("$PIOENV")
project_dir = Path(env.subst("$PROJECT_DIR"))
framework_dir = Path(env.PioPlatform().get_package_dir("framework-arduinoteensy"))
destination_dir = framework_dir / "cores" / "teensy4"

if pio_env == "teensy40_xinput":
    source_dir = project_dir / "third_party" / "ArduinoXInput_Teensy" / "teensy" / "avr" / "cores" / "teensy4"
    files = CORE_FILES + XINPUT_ONLY_FILES
    mode = "XInput"
else:
    source_dir = project_dir / "third_party" / "Teensyduino_1.60" / "cores" / "teensy4"
    files = CORE_FILES
    mode = "Teensyduino 1.60"
    for name in XINPUT_ONLY_FILES:
        extra_file = destination_dir / name
        if extra_file.exists():
            extra_file.unlink()

changed = []
for name in files:
    source = source_dir / name
    destination = destination_dir / name
    if not source.exists():
        raise FileNotFoundError(source)
    if copy_if_changed(source, destination):
        changed.append(name)

if changed:
    print(f"Applied {mode} core files: " + ", ".join(changed))
