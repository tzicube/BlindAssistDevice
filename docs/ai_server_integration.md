# App ↔ AI Server Integration

How the ClearPath AI Android app (this repo) talks to the AI server in
[BlindAssistDevice](https://github.com/tzicube/BlindAssistDevice) (`AiServer/test.py`), what was tested,
and what the server still needs before the finals demo.

**Status:** app side done and tested on the Android 17 emulator against a mock server and against the
server's own code with fake models. Not yet tested with the real GPU server (Whisper / Gemma / Piper).

## 1. Architecture

```
Glasses (XIAO ESP32S3) ──Wi-Fi TCP 8888──▶ Android app ──HTTP──▶ AI server (laptop, port 8765)
                                              ▲                    Whisper → Gemma (with image) → Piper
                                              └──── answer (WAV) ──┘
```

- The glasses keep sending only to the phone. **No firmware change is needed.**
- The phone is the hub: it forwards the current frame and the user's question to the server.
- **The server API is used as it is. No server code change is required for the connection.**
- All devices join the phone's hotspot; the app is given the laptop's IP address.

## 2. What the app sends

When the user presses **「問問題」 (Ask)**, hears a beep, and speaks (e.g. 「這是什麼」 "What is this?"):

| Step | Request | Body | Expected response |
|---|---|---|---|
| 1 | `POST /api/videoframe` | `image/jpeg`: the current camera frame (glasses: 320×240; phone camera: scaled to max 640 px wide, quality 85) | `200 {"status": true}` |
| 2 | `POST /api/recognize` | `audio/wav`: 16 kHz, mono, 16-bit PCM, 0.5–8 s | `200`, `audio/wav` (the spoken answer) |

- Step 1 always runs right before step 2, so `/api/recognize` always has a fresh "last frame".
- The app plays the returned WAV with Android `MediaPlayer` (Piper's 22.05 kHz mono WAV works).
- Recording stops automatically when the user stops talking (or after 7 s).

### Timeouts and cancelling

| Setting | Value |
|---|---|
| Connect timeout | 4 s |
| Read timeout | 90 s (the first question after server start also loads the models) |
| User cancels | the app closes the HTTP connection; the server may log a broken pipe, which is harmless |

While waiting, the app says 「還在分析，請稍等」 ("still analysing") every 10 s.

### Error handling

The app turns server errors into short spoken messages:

| Server response | What the user hears |
|---|---|
| Cannot connect / no route | 「連不上 AI 伺服器…」 (cannot reach the AI server) |
| Read timeout (90 s) | 「AI 伺服器回應太久…」 (server took too long) |
| `404` whose body contains "last image" | 「AI 伺服器沒有收到畫面…」 (server has no frame) |
| `400` | 「AI 伺服器不接受這個格式」 (format rejected) |
| Other `4xx` / `5xx`, empty answer | 「AI 伺服器處理失敗…」 (server failed) |

Details are logged in Logcat with the tag `ClearPath`.

## 3. What the server needs before the demo

Ordered by priority.

### 3.1 Switch to Chinese (required)

Users speak Mandarin. Today every part of the pipeline is set to English:

| File | Now | Suggested |
|---|---|---|
| `AiConfig.py` `WhisperSTTConfig.language` | `"en"` | `"zh"` |
| `AiConfig.py` `PiperTTSConfig.model_path` | `en_US-amy-medium.onnx` | `zh_CN-huayan-medium.onnx` ([Piper voices](https://huggingface.co/rhasspy/piper-voices/tree/main/zh/zh_CN/huayan/medium)) |
| `Recognize/process.py` `_build_prompt()` | English instructions | Ask for a reply in **Traditional Chinese, at most two short sentences**, e.g. 「你是協助視障者的助理。請根據最新的相機畫面，用繁體中文、最多兩句話簡短回答使用者的問題。畫面看不清楚時請直接說不確定。」 |

To check: whether the `zh_CN` Piper voice reads Traditional characters correctly. If it does not,
the prompt can ask for Simplified Chinese instead (only the voice hears it).

### 3.2 Configurable model path (required for running on another laptop)

`PiperTTSConfig.model_path` is hard-coded to `C:\Users\Admin\...`. Reading it from `.env`
(like `OLLAMA_BASE_URL`) lets whoever brings the GPU laptop run the server without editing code.

### 3.3 Privacy and robustness (recommended, patch ready)

Two small changes, already tested with the server's own code (models replaced by stand-ins):

1. **Delete recordings after each request.** `/api/recognize` keeps every user voice recording
   (`runtime/recognize_input/`) and every answer (`runtime/recognize_output/`) forever. The patch
   deletes both when the request ends (success or failure). Set `KEEP_RECOGNIZE_AUDIO=1` in `.env`
   to keep them for debugging.
2. **Limit the request size.** `read_request_body()` reads whatever `Content-Length` says into memory.
   The patch rejects bodies over 5 MB with `400` (a frame is ~10–40 KB, a question ~256 KB).

Tested: normal requests still return audio and leave no files; a 50 MB request is rejected with
`400`; with `KEEP_RECOGNIZE_AUDIO=1` the files are kept. 2 files, 27 lines:

<details>
<summary>Patch (apply in BlindAssistDevice with <code>git apply</code>)</summary>

```diff
diff --git a/AiServer/Recognize/process.py b/AiServer/Recognize/process.py
index 7d10d1e..6e6965b 100644
--- a/AiServer/Recognize/process.py
+++ b/AiServer/Recognize/process.py
@@ -109,6 +109,9 @@ OLLAMA_URL = _build_ollama_generate_url(
         "OLLAMA_BASE_URL",
     )
 )
+# The user's voice recordings and the generated answers are deleted after each request.
+# Set KEEP_RECOGNIZE_AUDIO=1 in .env to keep them for debugging.
+KEEP_AUDIO_FILES = _get_config_value(_ENV_VALUES, "KEEP_RECOGNIZE_AUDIO") == "1"
 
 
 def _normalize_content_type(content_type: str | None) -> str:
@@ -154,6 +157,15 @@ def _save_audio_request(audio_bytes: bytes) -> Path:
     return audio_path
 
 
+def _delete_quietly(path: Path | None) -> None:
+    if path is None or KEEP_AUDIO_FILES:
+        return
+    try:
+        path.unlink(missing_ok=True)
+    except OSError:
+        logger.warning("Could not delete audio file: %s", path)
+
+
 def _build_prompt(question: str) -> str:
     return (
         "You are assisting a blind user. "
@@ -245,6 +257,8 @@ def process_recognize_request(
             "No last image is available yet. Call /api/videoframe first."
         )
 
+    audio_path: Path | None = None
+    output_path: Path | None = None
     try:
         audio_path = _save_audio_request(audio_bytes)
 
@@ -280,3 +294,6 @@ def process_recognize_request(
     except Exception:
         logger.exception("Recognize pipeline failed")
         raise
+    finally:
+        _delete_quietly(audio_path)
+        _delete_quietly(output_path)
diff --git a/AiServer/test.py b/AiServer/test.py
index fd0c5d2..6de8463 100644
--- a/AiServer/test.py
+++ b/AiServer/test.py
@@ -16,6 +16,10 @@ RECOGNIZE_PATHS = {"/api/recognize", "/recognize"}
 IMAGE_PATHS = {"/api/image", "/image"}
 QUIET_REQUEST_PATHS = VIDEOFRAME_PATHS | IMAGE_PATHS
 
+# Largest request accepted. A QVGA JPEG is ~10 KB and an 8 s 16 kHz WAV is ~256 KB, so 5 MB is
+# plenty; without a limit one huge upload could use up the server's memory.
+MAX_REQUEST_BYTES = 5 * 1024 * 1024
+
 logging.basicConfig(
     level=logging.INFO,
     format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
@@ -123,6 +127,12 @@ class BlindAssistHandler(BaseHTTPRequestHandler):
 
     def read_request_body(self) -> bytes:
         content_length = int(self.headers.get("Content-Length", 0))
+        if content_length < 0 or content_length > MAX_REQUEST_BYTES:
+            # The body is not read, so this connection cannot be reused.
+            self.close_connection = True
+            raise ValueError(
+                f"Request body too large: {content_length} bytes (limit {MAX_REQUEST_BYTES})"
+            )
         return self.rfile.read(content_length)
 
     def send_json_response(self, status: HTTPStatus, payload: dict):
```

</details>

### 3.4 Demo checklist

- Run the server only on the **password-protected phone hotspot**, not school or public Wi-Fi:
  the server has no authentication, so anyone on the same network could read `/api/image`
  (the latest camera frame).
- **Warm up** before going on stage: ask one question first, because the first request loads Whisper
  and Gemma and can take much longer.
- Windows Firewall: allow Python on **Private and Public** networks (a phone hotspot is often treated as public).
- Note the laptop's IP on the hotspot; enter it in the app by **long-pressing 「問問題」**.

### 3.5 Optional ideas (not required)

- **Return the answer text too**, e.g. a response header `X-Answer-Text` (URL-encoded). The app could show
  it on screen, and could speak it with the phone's zh-TW voice if Piper's voice sounds unnatural.
- **Family dashboard live view:** the dashboard's camera panel reads `/api/image`, which the app now updates
  only when a question is asked. If the dashboard should show a live view, the app can also post a frame
  about once per second. Tell us which you prefer.

## 4. Testing without the GPU server

`tools/mock_ai_server.py` (this repo) has the same API and port and needs only Python 3:

```
python tools/mock_ai_server.py              # answers with a short chime
python tools/mock_ai_server.py --delay 5    # pretend the model takes 5 s
python tools/mock_ai_server.py --reply a.wav  # answer with your own WAV
```

It saves every received question and frame in `mock_ai_output/` (git-ignored) and prints the
recording's length and loudness, which is useful for checking the microphone.

In the app, long-press 「問問題」 and enter `10.0.2.2` on the Android Studio emulator, or the laptop's IP
on a real phone.

## 5. Other things that affect the server side

- **Android 17 local network permission.** The app targets SDK 37. On Android 17, apps targeting 37 need
  the runtime permission `ACCESS_LOCAL_NETWORK` to reach any LAN address; without it connections time
  out. The app now requests it. This also affects the glasses' Wi-Fi link
  ([Android documentation](https://developer.android.com/privacy-and-security/local-network-permission)).
- **Cleartext HTTP.** The server speaks plain HTTP, so the app allows cleartext traffic
  (`res/xml/network_security_config.xml`). Google Maps traffic is still HTTPS.
- **Glasses microphone (planned).** The XIAO ESP32S3 Sense has a built-in microphone. The plan is to send
  its audio to the phone over the existing TCP link (packet types `0x20` audio, `0x21` button, see
  `docs/esp32_protocol.md`). The phone would still post the same WAV to `/api/recognize`, so the
  server API does not change.

## 6. Where the code is

| Path | What |
|---|---|
| `android/app/src/main/java/com/blindassist/app/ask/AiServerClient.kt` | HTTP calls, timeouts, cancel, error messages |
| `ask/QuestionRecorder.kt`, `ask/SpeechEndDetector.kt`, `ask/WavEncoder.kt` | Recording, end-of-speech detection, WAV encoding |
| `ask/AnswerPlayer.kt` | Playing the answer |
| `MainActivity.kt` (section "Asking the AI server") | Button flow, permissions, cancel |
| `tools/mock_ai_server.py` | Mock server |
