# GP2040-CE Reference Notes

GP2040-CE is a useful reference, but FightingTeensy should copy the boundaries rather than the full implementation. GP2040-CE is built around RP2040, TinyUSB, protobuf storage, and a USB-network web UI. Teensy 4.0 with Arduino core has different USB descriptor constraints, so the first FightingTeensy configuration path stays USB Serial.

Useful concepts to adapt:

- Versioned settings with magic, size, and checksum.
- Defaults loaded first, stored settings validated second, and invalid settings reset safely.
- A distinct configuration mode that avoids normal controller reports.
- Per-input calibration and rapid-trigger thresholds stored persistently.
- Boot/config chords as a future user-facing entry point.

Reference files in `C:\Users\iori\src\GP2040-CE`:

- `src/storagemanager.cpp` and `headers/storagemanager.h`: typed access to decoded settings.
- `src/config_utils.cpp` and `lib/FlashPROM/src/FlashPROM.cpp`: flash persistence with size, magic, and CRC footer.
- `proto/config.proto`: schema-backed configuration model.
- `src/gp2040.cpp` and `src/gamepad.cpp`: GPIO debounce, mapping, hotkeys, and boot actions.
- `src/addons/he_trigger.cpp`: rapid-trigger style threshold handling.
- `src/webconfig.cpp`: PC-side configuration API model.

Near-term FightingTeensy direction:

- Keep EEPROM settings small and fixed-layout until the schema grows enough to justify protobuf or a binary TLV format.
- Keep Serial config as the recovery-safe path.
- Add a button-chord config entry later, but do not rely on it as the only recovery method.
- Treat XInput flashing as opt-in until the Teensy XInput core patch is proven stable on the exact PlatformIO Teensyduino version.
