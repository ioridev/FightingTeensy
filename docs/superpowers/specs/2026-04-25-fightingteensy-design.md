# FightingTeensy Design

## Goal

Create a new PlatformIO project for a Teensy 4.0 fighting controller with 8000 Hz target reporting, hall-effect magnetic directional switches, rapid-trigger actuation, EEPROM-backed settings, and a PC-side configuration tool.

## Architecture

The project is split into firmware and host tooling. Firmware owns input scanning, SOCD cleaning, XInput report generation, EEPROM persistence, and the serial configuration command handler. Host tooling owns user-facing calibration commands and display of live sensor values.

The first implementation uses two PlatformIO environments:

- `teensy40_xinput` builds the normal play firmware as XInput.
- `teensy40_config_serial` builds a serial configuration firmware for the PC tool.

The XInput environment applies the bundled Teensy core XInput patch before compilation. The serial configuration environment restores the bundled Teensyduino 1.60 core originals before compilation. This keeps the first version reproducible without depending on a manually patched global Arduino install. A later milestone can add boot-button descriptor switching in the Teensy core so one image can expose XInput normally and a configuration interface when requested.

## Firmware Data Model

Settings are stored in EEPROM as a versioned `ControllerSettings` struct with a magic value, size, version, and CRC. Each D-pad direction has a `KeyCalibration` with rest position, bottom position, press offset, release offset, rapid-trigger offset, and polarity.

Defaults are conservative and usable before calibration. Invalid or missing EEPROM data falls back to defaults.

## Input Behavior

The D-pad uses four hall sensor analog inputs. The starter mapping is pins 14-17, which are A0-A3 on Teensy 4.0. A key computes travel from the calibrated rest value. Static press/release thresholds handle normal actuation, and a rapid-trigger threshold releases the key when travel retreats from its peak by the configured amount.

SOCD defaults to neutral for left+right and up+down. An up-priority mode is represented in settings for later PC tool exposure.

## PC Tool

The first PC tool is a Python CLI. It sends line-oriented commands over USB Serial:

- `PING`
- `GET`
- `SAMPLE`
- `CAL REST`
- `SAVE`
- `RESET`

The CLI intentionally stays small so the firmware protocol can stabilize before building a GUI.

## Known Constraint

The current XInput USB mode in the patched Teensy core does not expose a normal CDC Serial interface. That makes a single always-XInput device with a COM-port config tool impractical without USB descriptor work. The initial two-firmware setup is a deliberate stepping stone toward boot-button configuration mode.
