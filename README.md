# FightingTeensy

FightingTeensy is a PlatformIO-based Teensy 4.0 fighting controller firmware for magnetic hall-effect directional switches, rapid-trigger style actuation, EEPROM-backed configuration, and an 8000 Hz target report loop.

This repository is a new-generation rewrite rather than a patch on top of `Precision-Fighting-Board`.

## Current Shape

- `env:teensy40_config_serial`: configuration firmware, built as USB Serial for the PC tool. This is the default environment.
- `env:teensy40_xinput`: normal play firmware, built as XInput. Build is allowed, but upload is guarded.
- `env:teensy40_xinput_selftest`: diagnostic XInput firmware that toggles buttons and D-pad without reading hardware inputs.
- EEPROM stores hall-sensor calibration and rapid-trigger settings.
- The firmware sends XInput reports on a 125 us cadence in normal mode.
- The PC tool can ping the board, read settings, sample hall values, calibrate rest positions, save, and reset.

The eventual target is a single firmware that boots as XInput normally and enters configuration mode when a defined button is held during USB attach. The initial implementation keeps XInput and Serial as separate PlatformIO environments because USB device descriptors are selected at build time in the Teensy Arduino core.

## Requirements

- Teensy 4.0
- PlatformIO
- Python 3.10+
- `pyserial` for the PC tool
- ArduinoXInput library
- Bundled Teensy XInput core patch under `third_party/ArduinoXInput_Teensy`
- Bundled Teensyduino 1.60 core originals under `third_party/Teensyduino_1.60`

Install host dependencies:

```powershell
python -m pip install pyserial
```

Build normal firmware:

```powershell
pio run -e teensy40_xinput
```

Build the XInput self-test firmware when Windows sees the controller but no input changes:

```powershell
pio run -e teensy40_xinput_selftest
```

The XInput build starts from the bundled Teensyduino 1.60 originals and applies a small XInput overlay before compilation. The serial config build restores the bundled Teensyduino 1.60 originals before compilation. Without the XInput overlay, ArduinoXInput falls back to debug output and the board will not behave as an XInput controller.

The upstream XInput patch used by the original Precision Fighting Board fork was based on Teensyduino 1.58. FightingTeensy does not copy those core files wholesale into the PlatformIO Teensyduino 1.60 package; it ports only the XInput-specific descriptor and transport pieces.

XInput upload is intentionally blocked unless you opt in:

```powershell
$env:FIGHTING_TEENSY_ALLOW_XINPUT_UPLOAD = "1"
pio run -e teensy40_xinput -t upload
Remove-Item Env:\FIGHTING_TEENSY_ALLOW_XINPUT_UPLOAD
```

Build serial configuration firmware:

```powershell
pio run -e teensy40_config_serial
```

## Default Pins

Magnetic D-pad inputs use Teensy 4.0 analog pins:

| Direction | Pin |
| --- | --- |
| Up | 14 / A0 |
| Down | 15 / A1 |
| Left | 16 / A2 |
| Right | 17 / A3 |

Digital buttons follow the original Precision Fighting Board layout where possible. Trigger pins are moved to 20 and 21 in this starter mapping to avoid colliding with the hall-sensor analog pins.

## PC Tool

Flash `teensy40_config_serial`, then run:

```powershell
python tools\fighting_teensy_cli.py --port COM7 ping
python tools\fighting_teensy_cli.py --port COM7 sample
python tools\fighting_teensy_cli.py --port COM7 cal-rest
python tools\fighting_teensy_cli.py --port COM7 save
```

Run `cal-rest` with all magnetic direction keys released before using XInput firmware on a fresh EEPROM. If the default rest value does not match the sensors, directions can appear stuck and SOCD cleaning may cancel them out.

Tune SOCD, report rate, and per-direction hall thresholds:

```powershell
python tools\fighting_teensy_cli.py --port COM7 set --socd neutral --rate-khz 8
python tools\fighting_teensy_cli.py --port COM7 set --key up --press 80 --release 45 --rapid 28 --active-low 1
python tools\fighting_teensy_cli.py --port COM7 cal-key --key up --point rest
python tools\fighting_teensy_cli.py --port COM7 cal-key --key up --point bottom
python tools\fighting_teensy_cli.py --port COM7 save
```

Use `monitor` to watch live hall readings:

```powershell
python tools\fighting_teensy_cli.py --port COM7 monitor --interval 0.05
```

## Verification

Host-side protocol tests:

```powershell
python -m unittest discover -s tests
```
