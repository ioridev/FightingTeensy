#include <Arduino.h>

#if defined(FIGHTING_TEENSY_XINPUT_MODE)
#include <XInput.h>
#endif

#include "magnetic_key.h"
#include "settings.h"

constexpr uint8_t HALL_PINS[FT_KEY_COUNT] = {14, 15, 16, 17};
constexpr uint8_t DIGITAL_SCAN_PINS[] = {
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13,
    18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
    30, 31, 32, 33,
};
constexpr const char *BUTTON_SETTING_NAMES[FT_BUTTON_COUNT] = {
    "a", "b", "x", "y", "lb", "rb", "back", "start", "l3", "r3", "logo", "lt", "rt",
};

ControllerSettings settings;
MagneticKey dpadKeys[FT_KEY_COUNT];

void rebootToBootloader() {
  delay(20);
  _reboot_Teensyduino_();
}

bool readButton(uint8_t pin) {
  return digitalRead(pin) == LOW;
}

void beginDigitalButton(uint8_t pin) {
  pinMode(pin, INPUT_PULLUP);
}

void beginInputs() {
  for (uint8_t i = 0; i < FT_BUTTON_COUNT; ++i) {
    beginDigitalButton(settings.buttonPins[i]);
  }

  for (uint8_t i = 0; i < FT_KEY_COUNT; ++i) {
    dpadKeys[i].begin(HALL_PINS[i], &settings.keys[i]);
  }
}

bool bootChordHeld() {
  if (readButton(settings.buttonPins[FT_BUTTON_START])) {
    return true;
  }

  const uint8_t defaultStartPin = FT_DEFAULT_BUTTON_PINS[FT_BUTTON_START];
  if (defaultStartPin != settings.buttonPins[FT_BUTTON_START]) {
    pinMode(defaultStartPin, INPUT_PULLUP);
    return readButton(defaultStartPin);
  }

  return false;
}

#if defined(FIGHTING_TEENSY_CONFIG_MODE)
void beginDigitalPinScan() {
  for (uint8_t i = 0; i < sizeof(DIGITAL_SCAN_PINS); ++i) {
    beginDigitalButton(DIGITAL_SCAN_PINS[i]);
  }
}
#endif

uint32_t reportIntervalUs() {
  return 1000UL / settings.reportRateKhz;
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
constexpr uint16_t CONFIG_COMMAND_MAX_LENGTH = 240;

String commandLine;

bool parseUint16(const String &value, uint16_t &out) {
  if (value.length() == 0) {
    return false;
  }
  for (uint16_t i = 0; i < value.length(); ++i) {
    if (!isDigit(value[i])) {
      return false;
    }
  }

  const long parsed = value.toInt();
  if (parsed < 0 || parsed > 1023) {
    return false;
  }

  out = static_cast<uint16_t>(parsed);
  return true;
}

bool parseUint8(const String &value, uint8_t &out) {
  uint16_t parsed = 0;
  if (!parseUint16(value, parsed) || parsed > 255) {
    return false;
  }
  out = static_cast<uint8_t>(parsed);
  return true;
}

bool isValidDigitalButtonPin(uint8_t pin) {
  return pin <= 33 && !(pin >= 14 && pin <= 17);
}

bool hasValidDigitalButtonPinMap(const ControllerSettings &candidate) {
  for (uint8_t i = 0; i < FT_BUTTON_COUNT; ++i) {
    if (!isValidDigitalButtonPin(candidate.buttonPins[i])) {
      return false;
    }
    for (uint8_t j = static_cast<uint8_t>(i + 1); j < FT_BUTTON_COUNT; ++j) {
      if (candidate.buttonPins[i] == candidate.buttonPins[j]) {
        return false;
      }
    }
  }
  return true;
}

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
    Serial.print(" key");
    Serial.print(i);
    Serial.print("_active_low=");
    Serial.print(settings.keys[i].activeLow);
  }
  for (uint8_t i = 0; i < FT_BUTTON_COUNT; ++i) {
    Serial.print(" btn_");
    Serial.print(BUTTON_SETTING_NAMES[i]);
    Serial.print("_pin=");
    Serial.print(settings.buttonPins[i]);
  }
  Serial.println();
}

void printDigitalPins() {
  Serial.print("PINS");
  for (uint8_t i = 0; i < sizeof(DIGITAL_SCAN_PINS); ++i) {
    const uint8_t pin = DIGITAL_SCAN_PINS[i];
    Serial.print(" pin");
    Serial.print(pin);
    Serial.print("=");
    Serial.print(readButton(pin) ? 1 : 0);
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

void calibrateKeyPoint(uint8_t keyIndex, bool bottom, uint16_t samples) {
  if (keyIndex >= FT_KEY_COUNT) {
    Serial.println("ERR invalid_key");
    return;
  }

  uint32_t sum = 0;
  for (uint16_t sample = 0; sample < samples; ++sample) {
    sum += analogRead(HALL_PINS[keyIndex]);
    delay(1);
  }

  const uint16_t value = static_cast<uint16_t>(sum / samples);
  if (bottom) {
    settings.keys[keyIndex].bottom = value;
  } else {
    settings.keys[keyIndex].rest = value;
  }

  finalizeSettings(settings);
  Serial.print("OK key_calibrated key=");
  Serial.print(keyIndex);
  Serial.print(" point=");
  Serial.print(bottom ? "bottom" : "rest");
  Serial.print(" value=");
  Serial.println(value);
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

bool applySettingToken(ControllerSettings &candidate, const String &token) {
  const int tokenLength = static_cast<int>(token.length());
  const int equals = token.indexOf('=');
  if (equals <= 0 || equals >= tokenLength - 1) {
    return false;
  }

  const String name = token.substring(0, equals);
  const String value = token.substring(equals + 1);

  if (name == "SOCD") {
    uint8_t mode = 0;
    if (!parseUint8(value, mode) || mode > SOCD_UP_PRIORITY) {
      return false;
    }
    candidate.socdMode = mode;
    return true;
  }

  if (name == "RATE_KHZ") {
    uint8_t rate = 0;
    if (!parseUint8(value, rate) || !(rate == 1 || rate == 2 || rate == 4 || rate == 8)) {
      return false;
    }
    candidate.reportRateKhz = rate;
    return true;
  }

  if (name.startsWith("BTN_") && name.endsWith("_PIN")) {
    const String buttonName = name.substring(4, name.length() - 4);
    uint8_t buttonIndex = FT_BUTTON_COUNT;
    for (uint8_t i = 0; i < FT_BUTTON_COUNT; ++i) {
      String expected(BUTTON_SETTING_NAMES[i]);
      expected.toUpperCase();
      if (buttonName == expected) {
        buttonIndex = i;
        break;
      }
    }
    if (buttonIndex >= FT_BUTTON_COUNT) {
      return false;
    }

    uint8_t pin = 0;
    if (!parseUint8(value, pin) || !isValidDigitalButtonPin(pin)) {
      return false;
    }
    candidate.buttonPins[buttonIndex] = pin;
    return true;
  }

  if (!name.startsWith("KEY") || name.length() < 6 || !isDigit(name[3]) || name[4] != '_') {
    return false;
  }

  const uint8_t keyIndex = static_cast<uint8_t>(name[3] - '0');
  if (keyIndex >= FT_KEY_COUNT) {
    return false;
  }

  const String field = name.substring(5);
  KeyCalibration &key = candidate.keys[keyIndex];

  if (field == "ACTIVE_LOW") {
    uint8_t activeLow = 0;
    if (!parseUint8(value, activeLow) || activeLow > 1) {
      return false;
    }
    key.activeLow = activeLow;
    return true;
  }

  uint16_t parsed = 0;
  if (!parseUint16(value, parsed)) {
    return false;
  }

  if (field == "REST") {
    key.rest = parsed;
  } else if (field == "BOTTOM") {
    key.bottom = parsed;
  } else if (field == "PRESS") {
    key.pressOffset = parsed;
  } else if (field == "RELEASE") {
    key.releaseOffset = parsed;
  } else if (field == "RAPID") {
    key.rapidTriggerOffset = parsed;
  } else {
    return false;
  }

  return true;
}

void handleSetCommand(const String &line) {
  ControllerSettings candidate = settings;
  const int lineLength = static_cast<int>(line.length());
  int start = 4;
  bool changed = false;

  while (start < lineLength) {
    while (start < lineLength && line[start] == ' ') {
      ++start;
    }
    if (start >= lineLength) {
      break;
    }

    int end = line.indexOf(' ', start);
    if (end < 0) {
      end = lineLength;
    }

    const String token = line.substring(start, end);
    if (!applySettingToken(candidate, token)) {
      Serial.print("ERR bad_setting ");
      Serial.println(token);
      return;
    }
    changed = true;
    start = end + 1;
  }

  if (!changed) {
    Serial.println("ERR no_settings");
    return;
  }

  if (!hasValidDigitalButtonPinMap(candidate)) {
    Serial.println("ERR bad_button_pins");
    return;
  }

  settings = candidate;
  for (uint8_t i = 0; i < FT_BUTTON_COUNT; ++i) {
    beginDigitalButton(settings.buttonPins[i]);
  }
  finalizeSettings(settings);
  Serial.println("OK set");
}

void handleCalCommand(const String &line) {
  if (line == "CAL REST") {
    calibrateRest(250);
    return;
  }

  if (!line.startsWith("CAL KEY ")) {
    Serial.println("ERR bad_calibration_command");
    return;
  }

  const int pointStart = line.lastIndexOf(' ');
  if (pointStart <= 8) {
    Serial.println("ERR bad_calibration_command");
    return;
  }

  const String keyText = line.substring(8, pointStart);
  const String point = line.substring(pointStart + 1);
  uint8_t keyIndex = 0;
  if (!parseUint8(keyText, keyIndex) || keyIndex >= FT_KEY_COUNT) {
    Serial.println("ERR invalid_key");
    return;
  }

  if (point == "REST") {
    calibrateKeyPoint(keyIndex, false, 250);
  } else if (point == "BOTTOM") {
    calibrateKeyPoint(keyIndex, true, 250);
  } else {
    Serial.println("ERR invalid_point");
  }
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
  } else if (line == "PINS") {
    printDigitalPins();
  } else if (line.startsWith("CAL ")) {
    handleCalCommand(line);
  } else if (line.startsWith("SET ")) {
    handleSetCommand(line);
  } else if (line == "SAVE") {
    finalizeSettings(settings);
    saveSettingsToEeprom(settings);
    Serial.println("OK saved");
  } else if (line == "RESET") {
    loadDefaultSettings(settings);
    saveSettingsToEeprom(settings);
    Serial.println("OK reset");
  } else if (line == "BOOTLOADER") {
    Serial.println("OK bootloader");
    Serial.flush();
    rebootToBootloader();
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
  delay(30);
  if (bootChordHeld()) {
    rebootToBootloader();
  }
  XInput.setAutoSend(false);
  XInput.begin();
#endif

#if defined(FIGHTING_TEENSY_CONFIG_MODE)
  beginDigitalPinScan();
  Serial.begin(115200);
  commandLine.reserve(CONFIG_COMMAND_MAX_LENGTH);
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
    } else if (commandLine.length() < CONFIG_COMMAND_MAX_LENGTH - 1) {
      commandLine += c;
    }
  }
#endif

#if defined(FIGHTING_TEENSY_XINPUT_MODE)
  #if defined(FIGHTING_TEENSY_XINPUT_SELF_TEST)
  const bool phase = (millis() / 500) % 2 == 0;
  XInput.setButton(BUTTON_A, phase);
  XInput.setButton(BUTTON_B, !phase);
  XInput.setDpad(phase, false, false, !phase);
  XInput.send();
  return;
  #endif

  static elapsedMicros sinceReport;
  if (sinceReport < reportIntervalUs()) {
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

  XInput.setButton(BUTTON_A, readButton(settings.buttonPins[FT_BUTTON_A]));
  XInput.setButton(BUTTON_B, readButton(settings.buttonPins[FT_BUTTON_B]));
  XInput.setButton(BUTTON_X, readButton(settings.buttonPins[FT_BUTTON_X]));
  XInput.setButton(BUTTON_Y, readButton(settings.buttonPins[FT_BUTTON_Y]));
  XInput.setButton(BUTTON_LB, readButton(settings.buttonPins[FT_BUTTON_LB]));
  XInput.setButton(BUTTON_RB, readButton(settings.buttonPins[FT_BUTTON_RB]));
  XInput.setButton(BUTTON_BACK, readButton(settings.buttonPins[FT_BUTTON_BACK]));
  XInput.setButton(BUTTON_START, readButton(settings.buttonPins[FT_BUTTON_START]));
  XInput.setButton(BUTTON_L3, readButton(settings.buttonPins[FT_BUTTON_L3]));
  XInput.setButton(BUTTON_R3, readButton(settings.buttonPins[FT_BUTTON_R3]));
  XInput.setButton(TRIGGER_LEFT, readButton(settings.buttonPins[FT_BUTTON_LT]));
  XInput.setButton(TRIGGER_RIGHT, readButton(settings.buttonPins[FT_BUTTON_RT]));
  XInput.setButton(BUTTON_LOGO, readButton(settings.buttonPins[FT_BUTTON_LOGO]));
  XInput.setDpad(dpadUp, dpadDown, dpadLeft, dpadRight);
  XInput.send();
#endif
}
