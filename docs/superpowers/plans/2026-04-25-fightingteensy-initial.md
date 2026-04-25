# FightingTeensy Initial Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the initial FightingTeensy repository with PlatformIO firmware, EEPROM-backed hall input settings, and a serial PC configuration CLI.

**Architecture:** Firmware is divided into settings persistence, magnetic key state, and the main XInput/config loops. Host tooling is a Python CLI with tested response parsing.

**Tech Stack:** Teensy 4.0, PlatformIO, Arduino framework, ArduinoXInput, EEPROM, Python unittest.

---

### Task 1: Project Skeleton

**Files:**
- Create: `platformio.ini`
- Create: `.gitignore`
- Create: `README.md`

- [x] Create the PlatformIO project with `teensy40_xinput` and `teensy40_config_serial` environments.
- [x] Add ignore rules for PlatformIO build outputs and Python caches.
- [x] Document build, config, and test commands.

### Task 2: Firmware Settings

**Files:**
- Create: `src/settings.h`
- Create: `src/settings.cpp`

- [x] Define `ControllerSettings` and `KeyCalibration`.
- [x] Add CRC validation and default settings.
- [x] Add EEPROM load, save, and reset helpers.

### Task 3: Magnetic Key Input

**Files:**
- Create: `src/magnetic_key.h`
- Create: `src/magnetic_key.cpp`

- [x] Add a hall-sensor key state machine.
- [x] Support active-low sensors, static press/release, and rapid-trigger release from peak travel.

### Task 4: Firmware Entrypoint

**Files:**
- Create: `src/main.cpp`

- [x] Add normal XInput mode with a 125 us report cadence.
- [x] Add serial configuration mode with `PING`, `GET`, `SAMPLE`, `CAL REST`, `SAVE`, and `RESET`.
- [x] Add SOCD neutral handling.

### Task 5: PC CLI

**Files:**
- Create: `tools/fighting_teensy_cli.py`
- Create: `tools/__init__.py`
- Create: `tests/test_cli_protocol.py`

- [x] Add a Python CLI for configuration firmware.
- [x] Add protocol parsing tests that run without connected hardware.

### Task 6: Verification

**Files:**
- No new files.

- [x] Run `python -m unittest discover -s tests`.
- [x] Run `pio run -e teensy40_xinput` when PlatformIO is available.
- [x] Run `pio run -e teensy40_config_serial` when PlatformIO is available.
