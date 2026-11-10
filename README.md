# BlindAssistGlasses

**BlindAssistGlasses** is an AI-powered assistive smart glasses project designed to help visually impaired users understand their surroundings.

The ESP32 camera captures images and transmits them to an Android device over Wi-Fi. The Android application performs on-device AI processing and provides environmental information to the user through speech.

## System Architecture

```text
XIAO ESP32S3 Sense  (camera + ultrasonic sensors)
      │
      │ Wi-Fi (phone hotspot, auto-discovery)
      │ JPEG + distances
      ▼
Android App
      │
      ├── Image Receiver
      ├── YOLO Object Detection
      ├── Camera + ultrasonic distance fusion
      ├── Google Maps walking navigation
      ├── Local LLM (planned)
      └── Text-to-Speech
              │
              ▼
             User
```

## Image Specification

| Item | Specification |
|---|---|
| Board | XIAO ESP32S3 Sense |
| Image Format | JPEG |
| Resolution | 320 × 240 |
| Target Frame Rate | 10 FPS |
| Transmission | Wi-Fi TCP (BLE is too slow for 10 FPS; ESP32-S3 has no Bluetooth Classic) |
| Measured | 10.1 FPS, ~4.6 KB per frame |
| AI Processing | On-device |

## Project Goals

- [x] Receive JPEG images from the ESP32 on Android
- [x] Achieve a target transmission rate of 10 FPS
- [x] Run YOLO object detection on the Android device
- [ ] Run a local LLM on the Android device
- [x] Provide environmental information using Text-to-Speech
- [x] Integrate the complete ESP32 → Android → AI → Speech pipeline

## Development Progress

### ESP32 Camera

- [x] Initialize XIAO ESP32S3 Sense camera
- [x] Capture images in JPEG format
- [x] Set image resolution to 320 × 240 (QVGA)
- [x] Store camera frame buffer in PSRAM
- [x] Verify complete JPEG data (`FF D8` → `FF D9`)
- [x] Stream JPEG images over Wi-Fi (`esp32/clearpath_glasses/`)
- [x] Reach 10 FPS (measured 10.1 FPS)
- [x] Read three ultrasonic sensors (left / centre / right)
- [ ] Verify ultrasonic sensors on hardware

### Android App

- [x] Find and connect to XIAO ESP32S3 Sense over Wi-Fi
- [x] Receive and decode JPEG images
- [x] Display received images with detection boxes
- [x] Integrate YOLO object detection (YOLOv8n, LiteRT)
- [x] Integrate Text-to-Speech obstacle warnings
- [x] Voice commands and Google Maps walking navigation
- [ ] Integrate Whisper speech recognition
- [ ] Ask questions about the current view through the AI server (app side done, needs on-device test)
- [ ] Integrate local LLM (Gemma)

## Project Structure

```text
BlindAssistGlasses/
├── android/       # Android application (open this folder in Android Studio)
├── esp32/
│   ├── clearpath_glasses/   # Glasses firmware (camera + ultrasonic over Wi-Fi)
│   ├── BlindAssist_ESP32/   # Camera capture test sketch
│   └── tools/               # PC test tools (fake glasses, stream receiver)
├── tools/         # mock_ai_server.py: stand-in for the AI server, no GPU needed
├── ai/            # AI models
├── docs/          # Documentation (android_app.md, esp32_protocol.md)
└── README.md
```

## Related Repository

[BlindAssistDevice](https://github.com/tzicube/BlindAssistDevice): AI server (Whisper + Gemma + Piper) and family dashboard.
The app's 「問問題」 button talks to its AI server; see `docs/ai_server_integration.md` (API, testing, what the server still needs).

## Status

🚧 Under Development
