# POST /api/videoframe

# Request:
Content-Type: image/jpeg
320x40
10 FPS2
# Response:
application/json
{
    "status": true
}
## Workflow
Continuously send images to the server, so the server can send the images to the web application.

# POST /api/location

## Request

Content-Type: application/json

```json
{
  "latitude": 24.990782,
  "longitude": 121.346525,
  "source": "esp-simulator"
}
```

## Response

The server returns the accepted coordinates and update time. `GET /api/status`
includes this location for the dashboard, and `DELETE /api/location` clears it
for a fresh test.

## Workflow

The ESP simulator (or ESP firmware) sends its latest GPS fix to the dashboard API
on port `8787`. The dashboard displays the coordinates and places a marker on the map.

# ===============================================================================================
# POST /api/recognize

## Request

Content-Type: audio/wav

## Response

Content-Type: audio/wav

## Workflow

When the user presses the object recognition button and asks a question such as "What is this?", the ESP device records the user's voice and sends the audio to the server.

The server uses Speech-to-Text (STT) to convert the recorded audio into text. The transcribed question and the latest frame (last frame) received from the video streaming service are then passed to Gemma 3 (4B), a multimodal AI model capable of understanding both visual and textual information.

The AI analyzes the latest frame together with the user's question and generates an appropriate textual response. This response is then converted into speech using Text-to-Speech (TTS).

Finally, the server returns the generated audio response in WAV format, allowing the user to hear the answer through the device speaker.

# ===============================================================================================
# GET /api/image

Response:
Content-Type: image/jpeg
Cache-Control: no-store

Body:
JPEG image bytes
Resolution: 320x240

## Workflow
Return the latest frame received from ESP32.
