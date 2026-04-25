#pragma once

#include <Arduino.h>

#include "settings.h"

class MagneticKey {
public:
  void begin(uint8_t analogPin, const KeyCalibration *calibration);
  bool update();
  bool pressed() const;
  uint16_t raw() const;
  int16_t travel() const;

private:
  int16_t currentTravel(uint16_t value) const;

  uint8_t pin_ = 0;
  const KeyCalibration *calibration_ = nullptr;
  bool pressed_ = false;
  uint16_t raw_ = 0;
  int16_t travel_ = 0;
  int16_t peakTravel_ = 0;
};

