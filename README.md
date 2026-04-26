# FightingTeensy

> [!WARNING]
> This is an experimental work-in-progress project. The firmware and PC tooling are not currently expected to work as a usable controller, and the repository exists for development and hardware bring-up only.

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

Digital buttons use the current FightingTeensy board wiring. Pins 14-17 are reserved for the hall-sensor D-pad inputs.

| Button | Default Pin |
| --- | --- |
| A | 0 |
| B | 1 |
| X | 2 |
| Y | 3 |
| LB | 21 |
| RB | 5 |
| Back | 20 |
| Start | 7 |
| L3 | 18 |
| R3 | 19 |
| Home | 9 |
| LT | 4 |
| RT | 8 |

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

Then open `http://127.0.0.1:8765/`. Use the Web UI while the board is running `teensy40_config_serial`; XInput firmware does not expose a COM port in this first version. The Web UI loads the current EEPROM-backed button pin mapping, can edit that mapping as a full set, and can scan non-hall pins while you press buttons to confirm the assembled wiring.

If the board is running XInput firmware, hold the physical config button on pin 7 while plugging in USB. This does not directly expose a COM port; the firmware enters the Teensy bootloader, then the Web UI's `Flash Config` button can write `teensy40_config_serial` without opening the case. After that flash completes, the board re-enumerates as USB Serial and the Web UI can load settings. The boot chord always checks physical pin 7 before any saved button mapping so a bad saved map does not lock out configuration entry.

Tune SOCD, report rate, and per-direction hall thresholds:

```powershell
python tools\fighting_teensy_cli.py --port COM7 set --socd neutral --rate-khz 8
python tools\fighting_teensy_cli.py --port COM7 set --button start --pin 6
python tools\fighting_teensy_cli.py --port COM7 set --key up --press 80 --release 80 --rapid 28 --active-low 1
python tools\fighting_teensy_cli.py --port COM7 cal-key --key up --point rest
python tools\fighting_teensy_cli.py --port COM7 cal-key --key up --point bottom
python tools\fighting_teensy_cli.py --port COM7 save
```

For hall directions, `rest` and `bottom` are raw ADC readings. `press` is the initial activation offset from idle. `rapid` is the rapid-trigger sensitivity: while pressed, moving back by this amount releases the key, and while rapid-released, pressing forward by this amount turns it back on. `release` is the static reset point used when rapid trigger is disabled or when the key returns near idle. Set `rapid` to `0` to disable rapid-trigger behavior and use static press/release thresholds.

Use `monitor` to watch live hall readings:

```powershell
python tools\fighting_teensy_cli.py --port COM7 monitor --interval 0.05
```

## Verification

Host-side protocol tests:

```powershell
python -m unittest discover -s tests
```
