#include <Arduino.h>

namespace {
constexpr uint8_t STATUS_LED_PIN = 2;
constexpr unsigned long BLINK_INTERVAL_MS = 500;

bool led_state = false;
unsigned long last_toggle_ms = 0;

void update_status_led() {
  const unsigned long now = millis();
  if (now - last_toggle_ms < BLINK_INTERVAL_MS) {
    return;
  }

  last_toggle_ms = now;
  led_state = !led_state;
  digitalWrite(STATUS_LED_PIN, led_state ? HIGH : LOW);
}
}  // namespace

void setup() {
  pinMode(STATUS_LED_PIN, OUTPUT);
  Serial.begin(115200);
  delay(500);

  Serial.println();
  Serial.println("ESP32 device firmware started.");
}

void loop() {
  update_status_led();
}
