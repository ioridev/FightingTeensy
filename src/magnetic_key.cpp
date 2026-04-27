#include "magnetic_key.h"

void MagneticKey::begin(uint8_t analogPin, const KeyCalibration *calibration) {
  pin_ = analogPin;
  calibration_ = calibration;
  pinMode(pin_, INPUT);
  raw_ = analogRead(pin_);
  travel_ = currentTravel(raw_);
  rapidAnchorTravel_ = travel_;
  requireRapidRepress_ = false;
  pressed_ = false;
}

bool MagneticKey::update() {
  raw_ = analogRead(pin_);
  travel_ = currentTravel(raw_);
  const int16_t rapidOffset = static_cast<int16_t>(calibration_->rapidTriggerOffset);

  if (rapidOffset > 0) {
    const int16_t pressOffset = static_cast<int16_t>(calibration_->pressOffset);
    const int16_t releaseOffset = static_cast<int16_t>(calibration_->releaseOffset);

    if (pressed_) {
      if (travel_ > rapidAnchorTravel_) {
        rapidAnchorTravel_ = travel_;
      }

      if (travel_ <= releaseOffset || rapidAnchorTravel_ - travel_ >= rapidOffset) {
        pressed_ = false;
        rapidAnchorTravel_ = travel_;
        requireRapidRepress_ = travel_ > releaseOffset;
      }
    } else {
      if (travel_ <= releaseOffset) {
        requireRapidRepress_ = false;
      }

      if (travel_ < rapidAnchorTravel_) {
        rapidAnchorTravel_ = travel_;
      }

      if (!requireRapidRepress_) {
        if (travel_ >= pressOffset) {
          pressed_ = true;
          rapidAnchorTravel_ = travel_;
        }
      } else if (travel_ >= pressOffset && travel_ - rapidAnchorTravel_ >= rapidOffset) {
        pressed_ = true;
        rapidAnchorTravel_ = travel_;
      }
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
