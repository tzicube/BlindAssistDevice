# POST /api/videoframe

# Request:
Content-Type: image/jpeg
320x240
10 FPS
# Response:
application/json
{
    "status": true
}
## Workflow
Continuously send images to the server, so the server can send the images to the web application.


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
