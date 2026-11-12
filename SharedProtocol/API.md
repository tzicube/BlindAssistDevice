# POST /api/videoframe

## Request

Content-Type: image/jpeg

- Resolution: 320x240
- Frame rate: 30 FPS

## Response

```json
{"status": true}
```

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

# POST /api/recognize

## Request

Content-Type: audio/wav

## Response

Legacy clients receive one complete `audio/wav` after the full answer is ready.

For low-latency sentence streaming, send:

```http
Accept: application/x-ndjson, audio/wav
```

The response uses chunked `application/x-ndjson`. Each completed sentence is
sent immediately as a Base64 WAV event, followed by a final `done` event:

```json
{"type":"audio","index":1,"text":"First sentence.","contentType":"audio/wav","audio":"UklGR..."}
{"type":"done","sentenceCount":1}
```

## Workflow

When the user presses the recognition button and asks a question, the device
records the user's voice and sends the audio to the server.

The server uses Whisper to convert the recording into text. The question and
latest camera frame are passed to the configured Gemma 3 model. Gemma's token
stream is split at `.`, `,`, `。`, `，`, `!`, `?`, `！`, or `？`, and the
configured persistent TTS voice converts each completed phrase into WAV
immediately. The current default is the local Windows SAPI voice Microsoft
Hanhan Desktop (`zh-TW`); Piper remains available as a configured fallback.

Streaming clients play every sentence as soon as its WAV event arrives. Clients
without the streaming `Accept` header continue to receive one complete WAV.

# POST /api/caution

Send an urgent safety event. `POST /ip/caution` is accepted as a compatibility
alias. The event is stored as the latest caution and included in
`GET /api/status`, allowing the dashboard to show a Traditional Chinese danger
popup on its next poll.

The popup intentionally omits both the street address and raw coordinates. It
shows only the safety information needed to react to the event.

```json
{
  "event": "fall",
  "message": "使用者可能跌倒",
  "sizeG": 0.85,
  "time": 1763000000000,
  "latitude": 24.990782,
  "longitude": 121.346525,
  "heading": 92.0,
  "direction": "東",
  "source": "android-app",
  "sensor": "esp32"
}
```

The server responds with HTTP `202` and the stored caution. Repeated payloads
with the same event, time, source and sensor use the same event ID so the
frontend does not reopen the same popup during every status poll.

# GET /api/image

Response:

- Content-Type: image/jpeg
- Cache-Control: no-store
- Resolution: 320x240

## Workflow

Return the latest frame received from ESP32.
