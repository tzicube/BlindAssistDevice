from __future__ import annotations

import base64
import json
import logging
import os
import uuid
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    from speech.stt import WhisperSTT
    from speech.tts import PiperTTS

from last_image_store import get_last_image_path, load_last_image_bytes


logger = logging.getLogger("blind_assist.recognize")

BASE_DIR = Path(__file__).resolve().parents[1]
RUNTIME_DIR = BASE_DIR / "runtime"
INPUT_AUDIO_DIR = RUNTIME_DIR / "recognize_input"
OUTPUT_AUDIO_DIR = RUNTIME_DIR / "recognize_output"

MODEL_NAME = os.getenv("VISION_MODEL_NAME", "gemma3:4b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
ALLOWED_CONTENT_TYPES = {"audio/wav", "audio/x-wav", "audio/wave"}

_stt_instance: WhisperSTT | None = None
_tts_instance: PiperTTS | None = None
_service_lock = Lock()


def _normalize_content_type(content_type: str | None) -> str:
    return (content_type or "").split(";", 1)[0].strip().lower()


def _get_stt() -> WhisperSTT:
    global _stt_instance

    if _stt_instance is None:
        with _service_lock:
            if _stt_instance is None:
                from speech.stt import WhisperSTT

                logger.info("Initializing Whisper STT service")
                _stt_instance = WhisperSTT()
                logger.info("Whisper STT service initialized")

    return _stt_instance


def _get_tts() -> PiperTTS:
    global _tts_instance

    if _tts_instance is None:
        with _service_lock:
            if _tts_instance is None:
                from speech.tts import PiperTTS

                logger.info("Initializing Piper TTS service")
                _tts_instance = PiperTTS()
                logger.info("Piper TTS service initialized")

    return _tts_instance


def _save_audio_request(audio_bytes: bytes) -> Path:
    INPUT_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    audio_path = INPUT_AUDIO_DIR / f"recognize_{uuid.uuid4().hex}.wav"

    logger.info("Saving incoming audio request to: %s", audio_path)
    audio_path.write_bytes(audio_bytes)
    return audio_path


def _build_prompt(question: str) -> str:
    return (
        "You are assisting a blind user. "
        "Use the latest camera image to answer the user's question clearly, naturally, and briefly. "
        "If the image does not provide enough evidence, say that honestly.\n"
        f"User question: {question}"
    )


def _ask_multimodal_model(question: str, image_bytes: bytes, image_path: Path) -> str:
    logger.info(
        "Encoding last image for multimodal request | path=%s | image_size=%s bytes",
        image_path,
        len(image_bytes),
    )
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "model": MODEL_NAME,
        "prompt": _build_prompt(question),
        "images": [image_base64],
        "stream": False,
    }

    request = Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    logger.info(
        "Sending multimodal request to Ollama | model=%s | url=%s",
        MODEL_NAME,
        OLLAMA_URL,
    )

    try:
        with urlopen(request, timeout=180) as response:
            raw_response = response.read().decode("utf-8")
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        logger.exception("Ollama HTTP error | status=%s", exc.code)
        raise RuntimeError(
            f"Ollama request failed with status {exc.code}: {error_body}"
        ) from exc
    except URLError as exc:
        logger.exception("Could not reach Ollama service")
        raise RuntimeError(f"Could not connect to Ollama: {exc.reason}") from exc

    logger.info("Received raw response from Ollama")
    response_data = json.loads(raw_response)
    answer = response_data.get("response", "").strip()

    if not answer:
        logger.error("Multimodal model returned an empty answer")
        raise RuntimeError("Multimodal model returned an empty answer")

    logger.info("Multimodal answer generated successfully | answer=%s", answer)
    return answer


def process_recognize_request(
    audio_bytes: bytes,
    content_type: str | None = None,
) -> bytes:
    normalized_content_type = _normalize_content_type(content_type)
    payload_size = len(audio_bytes)

    logger.info(
        "Recognize pipeline started | content_type=%s | payload_size=%s bytes",
        normalized_content_type or "missing",
        payload_size,
    )

    if normalized_content_type not in ALLOWED_CONTENT_TYPES:
        logger.error("Unsupported recognize content type: %s", normalized_content_type)
        raise ValueError("Content-Type must be audio/wav")

    if not audio_bytes:
        logger.error("Recognize payload is empty")
        raise ValueError("Audio payload is empty")

    last_image_path = get_last_image_path()
    last_image_bytes = load_last_image_bytes()

    if last_image_bytes is None:
        logger.error("Last image not found for recognize pipeline: %s", last_image_path)
        raise FileNotFoundError(
            "No last image is available yet. Call /api/videoframe first."
        )

    try:
        audio_path = _save_audio_request(audio_bytes)

        logger.info("Starting Speech-to-Text step")
        question = _get_stt().transcribe(audio_path)

        if not question:
            logger.error("Speech-to-Text returned empty text")
            raise RuntimeError("Speech-to-Text returned empty text")

        logger.info("Speech-to-Text completed | question=%s", question)

        logger.info("Starting multimodal reasoning step")
        answer_text = _ask_multimodal_model(
            question,
            last_image_bytes,
            last_image_path,
        )

        OUTPUT_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_AUDIO_DIR / f"answer_{uuid.uuid4().hex}.wav"

        logger.info("Starting Text-to-Speech step | output_path=%s", output_path)
        generated_audio_path = _get_tts().synthesize(answer_text, output_path=output_path)
        generated_audio = generated_audio_path.read_bytes()

        logger.info(
            "Recognize pipeline completed successfully | output_path=%s | output_size=%s bytes",
            generated_audio_path,
            len(generated_audio),
        )
        return generated_audio
    except Exception:
        logger.exception("Recognize pipeline failed")
        raise
