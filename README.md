# FightingTeensy

FightingTeensy is a PlatformIO-based Teensy 4.0 fighting controller firmware for magnetic hall-effect directional switches, rapid-trigger style actuation, EEPROM-backed configuration, and an 8000 Hz target report loop.

This repository is a new-generation rewrite rather than a patch on top of `Precision-Fighting-Board`.

## Current Shape

- `env:teensy40_config_serial`: configuration firmware, built as USB Serial for the PC tool. This is the default environment.
- `env:teensy40_xinput`: normal play firmware, built as XInput. Build is allowed, but upload is guarded.
- `env:teensy40_xinput_selftest`: diagnostic XInput firmware that toggles buttons and D-pad without reading hardware inputs.
- EEPROM stores hall-sensor calibration, rapid-trigger settings, and digital button pin mapping.
- The firmware sends XInput reports on a 125 us cadence in normal mode.
- The PC tools can ping the board, read settings, sample hall values, calibrate rest/bottom positions, tune rapid-trigger thresholds, save, and reset.

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

| Button | Default Pin |
| --- | --- |
| A | 11 |
| B | 12 |
| X | 8 |
| Y | 7 |
| LB | 10 |
| RB | 9 |
| Back | 5 |
| Start | 6 |
| L3 | 18 |
| R3 | 19 |
| Home | 4 |
| LT | 20 |
| RT | 21 |

## PC Tool

Flash `teensy40_config_serial`, then run:

```powershell
python tools\fighting_teensy_cli.py --port COM7 ping
python tools\fighting_teensy_cli.py --port COM7 sample
python tools\fighting_teensy_cli.py --port COM7 pins
python tools\fighting_teensy_cli.py --port COM7 cal-rest
python tools\fighting_teensy_cli.py --port COM7 save
```

Run `cal-rest` with all magnetic direction keys released before using XInput firmware on a fresh EEPROM. If the default rest value does not match the sensors, directions can appear stuck and SOCD cleaning may cancel them out.

Start the local Web UI for calibration and rapid-trigger tuning:

```powershell
python tools\fighting_teensy_web.py --port 8765
```

Then open `http://127.0.0.1:8765/`. Use the Web UI while the board is running `teensy40_config_serial`; XInput firmware does not expose a COM port in this first version. The Web UI can edit digital button pin mapping and scan non-hall pins while you press buttons, which helps confirm the assembled wiring.

If the board is running XInput firmware, hold Start while plugging in USB. The firmware will enter the Teensy bootloader, then the Web UI's `Flash Config` button can write `teensy40_config_serial` without opening the case. After tuning, use `Return XInput` to write the normal XInput firmware back.

Tune SOCD, report rate, and per-direction hall thresholds:

```powershell
python tools\fighting_teensy_cli.py --port COM7 set --socd neutral --rate-khz 8
python tools\fighting_teensy_cli.py --port COM7 set --button start --pin 6
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
