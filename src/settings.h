#pragma once

#include <Arduino.h>
#include <stddef.h>

constexpr uint8_t FT_KEY_COUNT = 4;
constexpr uint32_t FT_SETTINGS_MAGIC = 0x46544754UL;  // FTGT
constexpr uint16_t FT_SETTINGS_VERSION = 2;
constexpr int FT_EEPROM_ADDRESS = 0;
constexpr uint8_t FT_BUTTON_COUNT = 13;

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

enum DigitalButtonIndex : uint8_t {
  FT_BUTTON_A = 0,
  FT_BUTTON_B = 1,
  FT_BUTTON_X = 2,
  FT_BUTTON_Y = 3,
  FT_BUTTON_LB = 4,
  FT_BUTTON_RB = 5,
  FT_BUTTON_BACK = 6,
  FT_BUTTON_START = 7,
  FT_BUTTON_L3 = 8,
  FT_BUTTON_R3 = 9,
  FT_BUTTON_LOGO = 10,
  FT_BUTTON_LT = 11,
  FT_BUTTON_RT = 12,
};

constexpr uint8_t FT_DEFAULT_BUTTON_PINS[FT_BUTTON_COUNT] = {
    11, 12, 8, 7, 10, 9, 5, 6, 18, 19, 4, 20, 21,
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
  uint8_t buttonPins[FT_BUTTON_COUNT];
  uint8_t reserved[3];
  uint16_t crc;
};

uint16_t ftCrc16(const uint8_t *data, size_t length);
void loadDefaultSettings(ControllerSettings &settings);
bool validateSettings(const ControllerSettings &settings);
void finalizeSettings(ControllerSettings &settings);
bool loadSettingsFromEeprom(ControllerSettings &settings);
void saveSettingsToEeprom(const ControllerSettings &settings);
void resetSettingsInEeprom();
