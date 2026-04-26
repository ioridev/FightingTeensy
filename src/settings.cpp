#include "settings.h"

#include <EEPROM.h>

namespace {
constexpr uint16_t FT_SETTINGS_VERSION_V1 = 1;

struct ControllerSettingsV1 {
  uint32_t magic;
  uint16_t version;
  uint16_t size;
  KeyCalibration keys[FT_KEY_COUNT];
  uint8_t socdMode;
  uint8_t reportRateKhz;
  uint16_t reserved;
  uint16_t crc;
};

bool isAllowedReportRate(uint8_t rateKhz) {
  return rateKhz == 1 || rateKhz == 2 || rateKhz == 4 || rateKhz == 8;
}

bool isAdcRange(uint16_t value) {
  return value <= 1023;
}

bool validateKeyCalibration(const KeyCalibration &key) {
  if (!isAdcRange(key.rest) || !isAdcRange(key.bottom) ||
      !isAdcRange(key.pressOffset) || !isAdcRange(key.releaseOffset) ||
      !isAdcRange(key.rapidTriggerOffset)) {
    return false;
  }
  if (key.activeLow > 1) {
    return false;
  }
  if (key.releaseOffset > key.pressOffset) {
    return false;
  }
  return true;
}

bool isHallPin(uint8_t pin) {
  return pin >= 14 && pin <= 17;
}

bool validateButtonPin(uint8_t pin) {
  return pin <= 33 && !isHallPin(pin);
}

bool validateButtonPins(const uint8_t *pins) {
  for (uint8_t i = 0; i < FT_BUTTON_COUNT; ++i) {
    if (!validateButtonPin(pins[i])) {
      return false;
    }
    for (uint8_t j = static_cast<uint8_t>(i + 1); j < FT_BUTTON_COUNT; ++j) {
      if (pins[i] == pins[j]) {
        return false;
      }
    }
  }
  return true;
}

bool validateSettingsV1(const ControllerSettingsV1 &settings) {
  if (settings.magic != FT_SETTINGS_MAGIC) {
    return false;
  }
  if (settings.version != FT_SETTINGS_VERSION_V1) {
    return false;
  }
  if (settings.size != sizeof(ControllerSettingsV1)) {
    return false;
  }

  ControllerSettingsV1 copy = settings;
  const uint16_t expected = copy.crc;
  copy.crc = 0;
  if (ftCrc16(reinterpret_cast<const uint8_t *>(&copy), sizeof(copy)) != expected) {
    return false;
  }

  if (settings.socdMode > SOCD_UP_PRIORITY) {
    return false;
  }
  if (!isAllowedReportRate(settings.reportRateKhz)) {
    return false;
  }
  for (uint8_t i = 0; i < FT_KEY_COUNT; ++i) {
    if (!validateKeyCalibration(settings.keys[i])) {
      return false;
    }
  }

  return true;
}

void migrateSettingsV1(const ControllerSettingsV1 &oldSettings, ControllerSettings &settings) {
  loadDefaultSettings(settings);
  for (uint8_t i = 0; i < FT_KEY_COUNT; ++i) {
    settings.keys[i] = oldSettings.keys[i];
  }
  settings.socdMode = oldSettings.socdMode;
  settings.reportRateKhz = oldSettings.reportRateKhz;
  finalizeSettings(settings);
}
}

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
    settings.keys[i].releaseOffset = 80;
    settings.keys[i].rapidTriggerOffset = 28;
    settings.keys[i].activeLow = 1;
    settings.keys[i].reserved = 0;
  }

  settings.socdMode = SOCD_NEUTRAL;
  settings.reportRateKhz = 8;
  for (uint8_t i = 0; i < FT_BUTTON_COUNT; ++i) {
    settings.buttonPins[i] = FT_DEFAULT_BUTTON_PINS[i];
  }
  for (uint8_t i = 0; i < sizeof(settings.reserved); ++i) {
    settings.reserved[i] = 0;
  }
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
  if (ftCrc16(reinterpret_cast<const uint8_t *>(&copy), sizeof(copy)) != expected) {
    return false;
  }

  if (settings.socdMode > SOCD_UP_PRIORITY) {
    return false;
  }
  if (!isAllowedReportRate(settings.reportRateKhz)) {
    return false;
  }
  if (!validateButtonPins(settings.buttonPins)) {
    return false;
  }
  for (uint8_t i = 0; i < FT_KEY_COUNT; ++i) {
    if (!validateKeyCalibration(settings.keys[i])) {
      return false;
    }
  }

  return true;
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

  ControllerSettingsV1 oldSettings;
  EEPROM.get(FT_EEPROM_ADDRESS, oldSettings);
  if (validateSettingsV1(oldSettings)) {
    migrateSettingsV1(oldSettings, settings);
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
