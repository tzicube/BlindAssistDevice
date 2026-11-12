#!/usr/bin/env python3
"""Unified BlindAssist HTTP API for dashboard telemetry and AI requests."""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import socket
import sys
import time
from datetime import datetime
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Lock


ROOT = Path(__file__).resolve().parent


def _load_root_environment() -> None:
    """Load configuration from the root .env without overriding shell variables."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            os.environ.setdefault(key, value.strip().strip("\"'"))


_load_root_environment()

from Backend import places_server as backend_api  # noqa: E402
from AiServer.StreamVideoFrame.process import process_video_frame_request  # noqa: E402
from AiServer.imageProcess.last_image_store import load_last_image_bytes  # noqa: E402


HOST = os.getenv("SERVER_HOST", os.getenv("BACKEND_HOST", "0.0.0.0"))
PORT = int(os.getenv("SERVER_PORT", os.getenv("BACKEND_PORT", "8787")))
CAMERA_FPS = max(1, int(os.getenv("CAMERA_FPS", "10")))
MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_AUDIO_BYTES = 16 * 1024 * 1024

VIDEOFRAME_PATH = "/api/videoframe"
RECOGNIZE_PATH = "/api/recognize"
STREAMING_AUDIO_CONTENT_TYPE = "application/x-ndjson"
IMAGE_PATH = "/api/image"
HEALTH_PATH = "/api/health"
QUIET_REQUEST_PATHS = {VIDEOFRAME_PATH, IMAGE_PATH}

AI_MODE = "real"
MOCK_DELAY_SECONDS = 0.0
MOCK_REPLY: bytes | None = None
MOCK_SAVE_OUTPUT = True
MOCK_OUTPUT_DIR = ROOT / "mock_ai_output"
RECOGNIZE_LOCK = Lock()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("blind_assist.unified")


class RequestBodyError(ValueError):
    def __init__(self, status: HTTPStatus, message: str):
        super().__init__(message)
        self.status = status


class ExclusiveThreadingHTTPServer(ThreadingHTTPServer):
    """Refuse a second server on the same port, including on Windows."""

    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_EXCLUSIVEADDRUSE,
                1,
            )
        super().server_bind()

    def handle_error(self, request, client_address):
        error = sys.exception()
        if isinstance(error, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)):
            logger.info(
                "Client closed HTTP connection | client=%s:%s | error=%s",
                client_address[0],
                client_address[1],
                error,
            )
            return
        super().handle_error(request, client_address)


class UnifiedHandler(backend_api.PlacesHandler):
    protocol_version = "HTTP/1.1"

    def handle(self):
        try:
            super().handle()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as error:
            logger.info(
                "Client disconnected during HTTP request | client=%s:%s | error=%s",
                self.client_address[0],
                self.client_address[1],
                error,
            )

    def log_message(self, format, *args):
        if self.request_path in QUIET_REQUEST_PATHS:
            return
        logger.info("%s - %s", self.address_string(), format % args)

    def do_GET(self):
        if self.request_path == IMAGE_PATH:
            self.handle_image()
            return
        if self.request_path == HEALTH_PATH:
            self.send_json(
                HTTPStatus.OK,
                {
                    "status": True,
                    "service": "blindassist-unified",
                    "aiMode": AI_MODE,
                    "cameraFps": CAMERA_FPS,
                },
            )
            return
        super().do_GET()

    def do_POST(self):
        if self.request_path == VIDEOFRAME_PATH:
            self.handle_videoframe()
            return
        if self.request_path == RECOGNIZE_PATH:
            self.handle_recognize()
            return
        super().do_POST()

    def handle_videoframe(self):
        try:
            image_bytes = self.read_bounded_body(MAX_IMAGE_BYTES)
            result = process_video_frame_request(
                image_bytes,
                self.headers.get("Content-Type"),
            )
            self.send_json(HTTPStatus.OK, result)
        except RequestBodyError as error:
            self.send_ai_error(error.status, str(error))
        except ValueError as error:
            self.send_ai_error(HTTPStatus.BAD_REQUEST, str(error))
        except Exception as error:  # noqa: BLE001
            logger.exception("Video frame handler failed")
            self.send_ai_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(error))

    def handle_image(self):
        image_bytes = load_last_image_bytes()
        if image_bytes is None:
            self.send_ai_error(
                HTTPStatus.NOT_FOUND,
                "No last image is available yet. Call /api/videoframe first.",
                log_error=False,
            )
            return

        self.send_binary(
            HTTPStatus.OK,
            image_bytes,
            "image/jpeg",
            {
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Camera-FPS": str(CAMERA_FPS),
            },
        )

    def handle_recognize(self):
        if not RECOGNIZE_LOCK.acquire(blocking=False):
            self.send_ai_error(
                HTTPStatus.TOO_MANY_REQUESTS,
                "Another recognize request is already running.",
            )
            return

        try:
            audio_bytes = self.read_bounded_body(MAX_AUDIO_BYTES)
            content_type = self.headers.get("Content-Type")
            wants_stream = STREAMING_AUDIO_CONTENT_TYPE in (
                self.headers.get("Accept") or ""
            ).lower()
            if AI_MODE == "mock":
                audio_response = process_mock_recognize(audio_bytes, content_type)
                if wants_stream:
                    self.send_audio_stream(iter([(1, "Mock response.", audio_response)]))
                    return
            else:
                from AiServer.Recognize.process import (
                    process_recognize_request,
                    process_recognize_request_stream,
                )

                if wants_stream:
                    audio_stream = process_recognize_request_stream(
                        audio_bytes,
                        content_type,
                    )
                    self.send_audio_stream(audio_stream)
                    return
                audio_response = process_recognize_request(audio_bytes, content_type)
            self.send_binary(HTTPStatus.OK, audio_response, "audio/wav")
        except RequestBodyError as error:
            self.send_ai_error(error.status, str(error))
        except ValueError as error:
            self.send_ai_error(HTTPStatus.BAD_REQUEST, str(error))
        except FileNotFoundError as error:
            self.send_ai_error(HTTPStatus.NOT_FOUND, str(error))
        except Exception as error:  # noqa: BLE001
            logger.exception("Recognize handler failed")
            self.send_ai_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(error))
        finally:
            RECOGNIZE_LOCK.release()

    def send_audio_stream(self, audio_stream):
        """Send sentence-level WAV segments as flushable NDJSON HTTP chunks."""
        self.send_response(HTTPStatus.OK)
        self.send_header(
            "Content-Type",
            f"{STREAMING_AUDIO_CONTENT_TYPE}; charset=utf-8",
        )
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Cache-Control", "no-store, no-transform")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        sentence_count = 0
        try:
            for index, sentence, audio_bytes in audio_stream:
                sentence_count = index
                self.write_stream_event(
                    {
                        "type": "audio",
                        "index": index,
                        "text": sentence,
                        "contentType": "audio/wav",
                        "audio": base64.b64encode(audio_bytes).decode("ascii"),
                    }
                )

            self.write_stream_event(
                {"type": "done", "sentenceCount": sentence_count}
            )
        except OSError:
            logger.info("Streaming audio client disconnected")
        except Exception as error:  # noqa: BLE001
            logger.exception("Streaming audio response failed")
            try:
                self.write_stream_event({"type": "error", "error": str(error)})
            except OSError:
                pass
        finally:
            close_stream = getattr(audio_stream, "close", None)
            if close_stream is not None:
                try:
                    close_stream()
                except Exception:  # noqa: BLE001
                    logger.debug("Could not close audio stream cleanly", exc_info=True)
            try:
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
            except OSError:
                pass

    def write_stream_event(self, event: dict) -> None:
        payload = (
            json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        self.wfile.write(f"{len(payload):X}\r\n".encode("ascii"))
        self.wfile.write(payload)
        self.wfile.write(b"\r\n")
        self.wfile.flush()

    def read_bounded_body(self, maximum_bytes: int) -> bytes:
        raw_length = self.headers.get("Content-Length")
        try:
            content_length = int(raw_length or "0")
        except ValueError as error:
            raise RequestBodyError(
                HTTPStatus.BAD_REQUEST,
                "Invalid Content-Length",
            ) from error

        if content_length <= 0:
            raise RequestBodyError(HTTPStatus.BAD_REQUEST, "Request body is empty")
        if content_length > maximum_bytes:
            raise RequestBodyError(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                f"Request body exceeds {maximum_bytes} bytes",
            )
        return self.rfile.read(content_length)

    def send_binary(
        self,
        status: HTTPStatus,
        payload: bytes,
        content_type: str,
        extra_headers: dict[str, str] | None = None,
    ):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        if extra_headers:
            for name, value in extra_headers.items():
                self.send_header(name, value)
        self.end_headers()
        self.wfile.write(payload)

    def send_ai_error(
        self,
        status: HTTPStatus,
        message: str,
        *,
        log_error: bool = True,
    ):
        if log_error:
            logger.error("AI request failed | status=%s | message=%s", status, message)
        self.send_json(status, {"status": False, "error": message})


def _normalize_content_type(content_type: str | None) -> str:
    return (content_type or "").split(";", 1)[0].strip().lower()


def _build_chime_wav(sample_rate: int = 22_050) -> bytes:
    """Build a short in-memory WAV response for the integrated mock mode."""
    import io
    import math
    import struct
    import wave

    frames = bytearray()
    for frequency, duration in ((660, 0.18), (0, 0.06), (880, 0.25)):
        sample_count = int(sample_rate * duration)
        for index in range(sample_count):
            envelope = min(1.0, index / 400, (sample_count - index) / 400)
            value = (
                0
                if frequency == 0
                else int(
                    9_000
                    * envelope
                    * math.sin(2 * math.pi * frequency * index / sample_rate)
                )
            )
            frames.extend(struct.pack("<h", value))

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(bytes(frames))
    return buffer.getvalue()


def process_mock_recognize(audio_bytes: bytes, content_type: str | None) -> bytes:
    if _normalize_content_type(content_type) not in {
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
    }:
        raise ValueError("Content-Type must be audio/wav")
    if not audio_bytes:
        raise ValueError("Audio payload is empty")

    frame = load_last_image_bytes()
    if frame is None:
        raise FileNotFoundError(
            "No last image is available yet. Call /api/videoframe first."
        )

    if MOCK_SAVE_OUTPUT:
        stamp = datetime.now().strftime("%H%M%S_%f")
        MOCK_OUTPUT_DIR.mkdir(exist_ok=True)
        (MOCK_OUTPUT_DIR / f"question_{stamp}.wav").write_bytes(audio_bytes)
        (MOCK_OUTPUT_DIR / f"frame_{stamp}.jpg").write_bytes(frame)

    if MOCK_DELAY_SECONDS:
        time.sleep(MOCK_DELAY_SECONDS)
    if MOCK_REPLY is None:
        raise RuntimeError("Mock AI reply is not configured")
    return MOCK_REPLY


def configure_mock_ai(delay: float, reply_path: Path | None) -> None:
    global AI_MODE, MOCK_DELAY_SECONDS, MOCK_REPLY

    AI_MODE = "mock"
    MOCK_DELAY_SECONDS = max(0.0, delay)
    MOCK_REPLY = reply_path.read_bytes() if reply_path else _build_chime_wav()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the unified BlindAssist backend and AI API."
    )
    parser.add_argument(
        "--mock-ai",
        action="store_true",
        help="Return a chime instead of running Whisper, Ollama and TTS.",
    )
    parser.add_argument("--mock-delay", type=float, default=0.0)
    parser.add_argument("--mock-reply", type=Path)
    args = parser.parse_args()

    if args.mock_ai:
        configure_mock_ai(args.mock_delay, args.mock_reply)

    backend_api.database.initialize()
    try:
        server = ExclusiveThreadingHTTPServer((HOST, PORT), UnifiedHandler)
    except OSError as error:
        logger.error("Cannot bind unified server to %s:%s: %s", HOST, PORT, error)
        return 1

    recognize_process = None
    if AI_MODE == "real":
        try:
            from AiServer.Recognize import process as recognize_process

            recognize_process.preload_ollama_model()
            recognize_process.preload_speech_services()
        except Exception:  # noqa: BLE001
            logger.exception("AI startup failed; unified server was not started")
            server.server_close()
            return 1

    logger.info(
        "Unified server running at http://%s:%s | AI mode=%s | camera=%s FPS",
        HOST,
        PORT,
        AI_MODE,
        CAMERA_FPS,
    )
    logger.info(
        "Endpoints include /api/status, /api/telemetry, /api/location, /api/places, "
        "/api/navigation/resolve, /api/caution, /api/image, /api/videoframe and "
        "/api/recognize"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    finally:
        server.server_close()
        if recognize_process is not None:
            try:
                recognize_process.shutdown_speech_services()
            except Exception:  # noqa: BLE001
                logger.exception("Could not shut down speech services cleanly")
            try:
                recognize_process.unload_ollama_model()
            except Exception:  # noqa: BLE001
                logger.exception("Could not unload Ollama model during shutdown")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
