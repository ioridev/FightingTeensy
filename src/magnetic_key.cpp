#include "magnetic_key.h"

void MagneticKey::begin(uint8_t analogPin, const KeyCalibration *calibration) {
  pin_ = analogPin;
  calibration_ = calibration;
  pinMode(pin_, INPUT);
  raw_ = analogRead(pin_);
  travel_ = currentTravel(raw_);
  lastRapidTravel_ = travel_;
  pressed_ = false;
}

bool MagneticKey::update() {
  raw_ = analogRead(pin_);
  travel_ = currentTravel(raw_);
  const int16_t rapidOffset = static_cast<int16_t>(calibration_->rapidTriggerOffset);

  if (rapidOffset > 0) {
    const bool pressing = travel_ > lastRapidTravel_ + rapidOffset;
    const bool releasing = lastRapidTravel_ > travel_ + rapidOffset;

    if (pressing || releasing) {
      lastRapidTravel_ = travel_;
    }

    if (!pressed_ && pressing && travel_ >= static_cast<int16_t>(calibration_->pressOffset)) {
      pressed_ = true;
    } else if (pressed_ && releasing &&
               travel_ <= static_cast<int16_t>(calibration_->releaseOffset)) {
      pressed_ = false;
    }

    return pressed_;
  }

  if (!pressed_ && travel_ >= static_cast<int16_t>(calibration_->pressOffset)) {
    pressed_ = true;
  } else if (pressed_ && travel_ <= static_cast<int16_t>(calibration_->releaseOffset)) {
    pressed_ = false;
  }

  return pressed_;
}

bool MagneticKey::pressed() const {
  return pressed_;
}

uint16_t MagneticKey::raw() const {
  return raw_;
}

int16_t MagneticKey::travel() const {
  return travel_;
}

int16_t MagneticKey::currentTravel(uint16_t value) const {
  if (calibration_ == nullptr) {
    return 0;
  }

  const int16_t rest = static_cast<int16_t>(calibration_->rest);
  const int16_t rawValue = static_cast<int16_t>(value);
  const int16_t travel = calibration_->activeLow ? rest - rawValue : rawValue - rest;
  return travel < 0 ? 0 : travel;
}
