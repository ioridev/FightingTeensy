#pragma once

#include <Arduino.h>
#include <stddef.h>

constexpr uint8_t FT_KEY_COUNT = 4;
constexpr uint32_t FT_SETTINGS_MAGIC = 0x46544754UL;  // FTGT
constexpr uint16_t FT_SETTINGS_VERSION = 1;
constexpr int FT_EEPROM_ADDRESS = 0;

enum DpadKeyIndex : uint8_t {
  FT_KEY_UP = 0,
  FT_KEY_DOWN = 1,
  FT_KEY_LEFT = 2,
  FT_KEY_RIGHT = 3,
};

enum SocdMode : uint8_t {
  SOCD_NEUTRAL = 0,
  SOCD_UP_PRIORITY = 1,
};

struct KeyCalibration {
  uint16_t rest;
  uint16_t bottom;
  uint16_t pressOffset;
  uint16_t releaseOffset;
  uint16_t rapidTriggerOffset;
  uint8_t activeLow;
  uint8_t reserved;
};

struct ControllerSettings {
  uint32_t magic;
  uint16_t version;
  uint16_t size;
  KeyCalibration keys[FT_KEY_COUNT];
  uint8_t socdMode;
  uint8_t reportRateKhz;
  uint16_t reserved;
  uint16_t crc;
};

uint16_t ftCrc16(const uint8_t *data, size_t length);
void loadDefaultSettings(ControllerSettings &settings);
bool validateSettings(const ControllerSettings &settings);
void finalizeSettings(ControllerSettings &settings);
bool loadSettingsFromEeprom(ControllerSettings &settings);
void saveSettingsToEeprom(const ControllerSettings &settings);
void resetSettingsInEeprom();
