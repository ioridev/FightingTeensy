#include "magnetic_key.h"

void MagneticKey::begin(uint8_t analogPin, const KeyCalibration *calibration) {
  pin_ = analogPin;
  calibration_ = calibration;
  pinMode(pin_, INPUT);
  raw_ = analogRead(pin_);
  travel_ = currentTravel(raw_);
  peakTravel_ = travel_;
  pressed_ = false;
}

bool MagneticKey::update() {
  raw_ = analogRead(pin_);
  travel_ = currentTravel(raw_);

  if (!pressed_) {
    peakTravel_ = travel_;
    if (travel_ >= static_cast<int16_t>(calibration_->pressOffset)) {
      pressed_ = true;
      peakTravel_ = travel_;
    }
    return pressed_;
  }

  if (travel_ > peakTravel_) {
    peakTravel_ = travel_;
  }

  const bool releasedByStaticPoint =
      travel_ <= static_cast<int16_t>(calibration_->releaseOffset);
  const bool releasedByRapidTrigger =
      calibration_->rapidTriggerOffset > 0 &&
      travel_ + static_cast<int16_t>(calibration_->rapidTriggerOffset) < peakTravel_;

  if (releasedByStaticPoint || releasedByRapidTrigger) {
    pressed_ = false;
    peakTravel_ = travel_;
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

