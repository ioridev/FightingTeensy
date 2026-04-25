#include <Arduino.h>

#if defined(FIGHTING_TEENSY_XINPUT_MODE)
#include <XInput.h>
#endif

#include "magnetic_key.h"
#include "settings.h"

constexpr uint8_t PIN_BUTTON_A = 11;
constexpr uint8_t PIN_BUTTON_B = 12;
constexpr uint8_t PIN_BUTTON_X = 8;
constexpr uint8_t PIN_BUTTON_Y = 7;
constexpr uint8_t PIN_BUTTON_LB = 10;
constexpr uint8_t PIN_BUTTON_RB = 9;
constexpr uint8_t PIN_BUTTON_BACK = 5;
constexpr uint8_t PIN_BUTTON_START = 6;
constexpr uint8_t PIN_BUTTON_L3 = 18;
constexpr uint8_t PIN_BUTTON_R3 = 19;
constexpr uint8_t PIN_BUTTON_LOGO = 4;
constexpr uint8_t PIN_TRIGGER_L = 20;
constexpr uint8_t PIN_TRIGGER_R = 21;

constexpr uint8_t HALL_PINS[FT_KEY_COUNT] = {14, 15, 16, 17};
constexpr uint32_t REPORT_INTERVAL_US = 125;

ControllerSettings settings;
MagneticKey dpadKeys[FT_KEY_COUNT];

bool readButton(uint8_t pin) {
  return digitalRead(pin) == LOW;
}

void beginDigitalButton(uint8_t pin) {
  pinMode(pin, INPUT_PULLUP);
}

void beginInputs() {
  beginDigitalButton(PIN_BUTTON_A);
  beginDigitalButton(PIN_BUTTON_B);
  beginDigitalButton(PIN_BUTTON_X);
  beginDigitalButton(PIN_BUTTON_Y);
  beginDigitalButton(PIN_BUTTON_LB);
  beginDigitalButton(PIN_BUTTON_RB);
  beginDigitalButton(PIN_BUTTON_BACK);
  beginDigitalButton(PIN_BUTTON_START);
  beginDigitalButton(PIN_BUTTON_L3);
  beginDigitalButton(PIN_BUTTON_R3);
  beginDigitalButton(PIN_BUTTON_LOGO);
  beginDigitalButton(PIN_TRIGGER_L);
  beginDigitalButton(PIN_TRIGGER_R);

  for (uint8_t i = 0; i < FT_KEY_COUNT; ++i) {
    dpadKeys[i].begin(HALL_PINS[i], &settings.keys[i]);
  }
}

void applySocd(bool &up, bool &down, bool &left, bool &right) {
  if (left && right) {
    left = false;
    right = false;
  }

  if (up && down) {
    if (settings.socdMode == SOCD_UP_PRIORITY) {
      down = false;
    } else {
      up = false;
      down = false;
    }
  }
}

#if defined(FIGHTING_TEENSY_CONFIG_MODE)
String commandLine;

void printSettings() {
  Serial.print("SETTINGS");
  Serial.print(" socd=");
  Serial.print(settings.socdMode);
  Serial.print(" rate_khz=");
  Serial.print(settings.reportRateKhz);
  for (uint8_t i = 0; i < FT_KEY_COUNT; ++i) {
    Serial.print(" key");
    Serial.print(i);
    Serial.print("_rest=");
    Serial.print(settings.keys[i].rest);
    Serial.print(" key");
    Serial.print(i);
    Serial.print("_bottom=");
    Serial.print(settings.keys[i].bottom);
    Serial.print(" key");
    Serial.print(i);
    Serial.print("_press=");
    Serial.print(settings.keys[i].pressOffset);
    Serial.print(" key");
    Serial.print(i);
    Serial.print("_release=");
    Serial.print(settings.keys[i].releaseOffset);
    Serial.print(" key");
    Serial.print(i);
    Serial.print("_rapid=");
    Serial.print(settings.keys[i].rapidTriggerOffset);
  }
  Serial.println();
}

void printSample() {
  Serial.print("SAMPLE");
  for (uint8_t i = 0; i < FT_KEY_COUNT; ++i) {
    dpadKeys[i].update();
    Serial.print(" key");
    Serial.print(i);
    Serial.print("_raw=");
    Serial.print(dpadKeys[i].raw());
    Serial.print(" key");
    Serial.print(i);
    Serial.print("_travel=");
    Serial.print(dpadKeys[i].travel());
  }
  Serial.println();
}

void calibrateRest(uint16_t samples) {
  uint32_t sums[FT_KEY_COUNT] = {0, 0, 0, 0};
  for (uint16_t sample = 0; sample < samples; ++sample) {
    for (uint8_t i = 0; i < FT_KEY_COUNT; ++i) {
      sums[i] += analogRead(HALL_PINS[i]);
    }
    delay(1);
  }

  for (uint8_t i = 0; i < FT_KEY_COUNT; ++i) {
    settings.keys[i].rest = static_cast<uint16_t>(sums[i] / samples);
  }
  finalizeSettings(settings);
  Serial.println("OK rest_calibrated");
}

void handleCommand(String line) {
  line.trim();
  line.toUpperCase();

  if (line == "PING") {
    Serial.println("OK FightingTeensy 0.1");
  } else if (line == "GET") {
    printSettings();
  } else if (line == "SAMPLE") {
    printSample();
  } else if (line == "CAL REST") {
    calibrateRest(250);
  } else if (line == "SAVE") {
    finalizeSettings(settings);
    saveSettingsToEeprom(settings);
    Serial.println("OK saved");
  } else if (line == "RESET") {
    loadDefaultSettings(settings);
    saveSettingsToEeprom(settings);
    Serial.println("OK reset");
  } else {
    Serial.print("ERR unknown_command ");
    Serial.println(line);
  }
}
#endif

void setup() {
  loadSettingsFromEeprom(settings);
  beginInputs();

#if defined(FIGHTING_TEENSY_XINPUT_MODE)
  XInput.setAutoSend(false);
  XInput.begin();
#endif

#if defined(FIGHTING_TEENSY_CONFIG_MODE)
  Serial.begin(115200);
  commandLine.reserve(64);
  while (!Serial && millis() < 1500) {
  }
  Serial.println("OK FightingTeensy config");
#endif
}

void loop() {
#if defined(FIGHTING_TEENSY_CONFIG_MODE)
  while (Serial.available() > 0) {
    const char c = static_cast<char>(Serial.read());
    if (c == '\n' || c == '\r') {
      if (commandLine.length() > 0) {
        handleCommand(commandLine);
        commandLine = "";
      }
    } else if (commandLine.length() < 63) {
      commandLine += c;
    }
  }
#endif

#if defined(FIGHTING_TEENSY_XINPUT_MODE)
  static elapsedMicros sinceReport;
  if (sinceReport < REPORT_INTERVAL_US) {
    return;
  }
  sinceReport = 0;

  const bool up = dpadKeys[FT_KEY_UP].update();
  const bool down = dpadKeys[FT_KEY_DOWN].update();
  const bool left = dpadKeys[FT_KEY_LEFT].update();
  const bool right = dpadKeys[FT_KEY_RIGHT].update();

  bool dpadUp = up;
  bool dpadDown = down;
  bool dpadLeft = left;
  bool dpadRight = right;
  applySocd(dpadUp, dpadDown, dpadLeft, dpadRight);

  XInput.setButton(BUTTON_A, readButton(PIN_BUTTON_A));
  XInput.setButton(BUTTON_B, readButton(PIN_BUTTON_B));
  XInput.setButton(BUTTON_X, readButton(PIN_BUTTON_X));
  XInput.setButton(BUTTON_Y, readButton(PIN_BUTTON_Y));
  XInput.setButton(BUTTON_LB, readButton(PIN_BUTTON_LB));
  XInput.setButton(BUTTON_RB, readButton(PIN_BUTTON_RB));
  XInput.setButton(BUTTON_BACK, readButton(PIN_BUTTON_BACK));
  XInput.setButton(BUTTON_START, readButton(PIN_BUTTON_START));
  XInput.setButton(BUTTON_L3, readButton(PIN_BUTTON_L3));
  XInput.setButton(BUTTON_R3, readButton(PIN_BUTTON_R3));
  XInput.setButton(TRIGGER_LEFT, readButton(PIN_TRIGGER_L));
  XInput.setButton(TRIGGER_RIGHT, readButton(PIN_TRIGGER_R));
  XInput.setButton(BUTTON_LOGO, readButton(PIN_BUTTON_LOGO));
  XInput.setDpad(dpadUp, dpadDown, dpadLeft, dpadRight);
  XInput.send();
#endif
}
