#include "settings.h"

#include <EEPROM.h>

uint16_t ftCrc16(const uint8_t *data, size_t length) {
  uint16_t crc = 0xFFFF;
  for (size_t i = 0; i < length; ++i) {
    crc ^= static_cast<uint16_t>(data[i]) << 8;
    for (uint8_t bit = 0; bit < 8; ++bit) {
      if (crc & 0x8000) {
        crc = static_cast<uint16_t>((crc << 1) ^ 0x1021);
      } else {
        crc = static_cast<uint16_t>(crc << 1);
      }
    }
  }
  return crc;
}

void loadDefaultSettings(ControllerSettings &settings) {
  settings.magic = FT_SETTINGS_MAGIC;
  settings.version = FT_SETTINGS_VERSION;
  settings.size = sizeof(ControllerSettings);

  for (uint8_t i = 0; i < FT_KEY_COUNT; ++i) {
    settings.keys[i].rest = 512;
    settings.keys[i].bottom = 128;
    settings.keys[i].pressOffset = 80;
    settings.keys[i].releaseOffset = 45;
    settings.keys[i].rapidTriggerOffset = 28;
    settings.keys[i].activeLow = 1;
    settings.keys[i].reserved = 0;
  }

  settings.socdMode = SOCD_NEUTRAL;
  settings.reportRateKhz = 8;
  settings.reserved = 0;
  finalizeSettings(settings);
}

bool validateSettings(const ControllerSettings &settings) {
  if (settings.magic != FT_SETTINGS_MAGIC) {
    return false;
  }
  if (settings.version != FT_SETTINGS_VERSION) {
    return false;
  }
  if (settings.size != sizeof(ControllerSettings)) {
    return false;
  }

  ControllerSettings copy = settings;
  const uint16_t expected = copy.crc;
  copy.crc = 0;
  return ftCrc16(reinterpret_cast<const uint8_t *>(&copy), sizeof(copy)) == expected;
}

void finalizeSettings(ControllerSettings &settings) {
  settings.magic = FT_SETTINGS_MAGIC;
  settings.version = FT_SETTINGS_VERSION;
  settings.size = sizeof(ControllerSettings);
  settings.crc = 0;
  settings.crc = ftCrc16(reinterpret_cast<const uint8_t *>(&settings), sizeof(settings));
}

bool loadSettingsFromEeprom(ControllerSettings &settings) {
  EEPROM.get(FT_EEPROM_ADDRESS, settings);
  if (validateSettings(settings)) {
    return true;
  }

  loadDefaultSettings(settings);
  return false;
}

void saveSettingsToEeprom(const ControllerSettings &settings) {
  EEPROM.put(FT_EEPROM_ADDRESS, settings);
}

void resetSettingsInEeprom() {
  ControllerSettings settings;
  loadDefaultSettings(settings);
  saveSettingsToEeprom(settings);
}

