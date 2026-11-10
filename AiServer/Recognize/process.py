from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from AiServer.AiConfig import AssistantConfig

if TYPE_CHECKING:
    from AiServer.speech.stt import WhisperSTT
    from AiServer.speech.tts import PiperTTS

from AiServer.imageProcess.last_image_store import load_last_image_bytes


logger = logging.getLogger("blind_assist.recognize")

BASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BASE_DIR.parent
ENV_PATH = REPO_ROOT / ".env"
RUNTIME_DIR = BASE_DIR / "runtime"
ALLOWED_CONTENT_TYPES = {"audio/wav", "audio/x-wav", "audio/wave"}

_stt_instance: WhisperSTT | None = None
_tts_instance: PiperTTS | None = None
_service_lock = Lock()


def _parse_dotenv(env_path: Path) -> dict[str, str]:
    if not env_path.exists():
        logger.warning(".env file not found at %s", env_path)
        return {}

    env_values: dict[str, str] = {}

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")

        if key:
            env_values[key] = value

    return env_values


def _get_config_value(
    env_values: dict[str, str],
    *keys: str,
) -> str | None:
    for key in keys:
        value = os.getenv(key) or env_values.get(key)
        if value:
            return value

    return None


def _get_required_config_value(
    env_values: dict[str, str],
    *keys: str,
) -> str:
    value = _get_config_value(env_values, *keys)

    if value:
        return value

    expected_keys = ", ".join(keys)
    raise RuntimeError(
        f"Missing required config in {ENV_PATH}: {expected_keys}"
    )


def _build_ollama_generate_url(raw_value: str) -> str:
    cleaned_value = raw_value.strip().rstrip("/")

    if cleaned_value.endswith("/api/generate"):
        return cleaned_value

    return f"{cleaned_value}/api/generate"


_ENV_VALUES = _parse_dotenv(ENV_PATH)
MODEL_NAME = _get_required_config_value(
    _ENV_VALUES,
    "OLLAMA_image_processing_MODEL",
)
OLLAMA_URL = _build_ollama_generate_url(
    _get_required_config_value(
        _ENV_VALUES,
        "OLLAMA_BASE_URL",
    )
)
ASSISTANT_CONFIG = AssistantConfig(
    name=_get_config_value(_ENV_VALUES, "AI_ASSISTANT_NAME") or "BlindAssist",
    role=(
        _get_config_value(_ENV_VALUES, "AI_ASSISTANT_ROLE")
        or "assistive visual and situational-awareness AI"
    ),
    audience=(
        _get_config_value(_ENV_VALUES, "AI_ASSISTANT_AUDIENCE")
        or "a blind or low-vision user"
    ),
    task=(
        _get_config_value(_ENV_VALUES, "AI_ASSISTANT_TASK")
        or (
            "analyze the latest camera image, answer the user's spoken question, "
            "identify relevant objects or obstacles, and prioritize urgent hazards"
        )
    ),
    operating_context=(
        _get_config_value(_ENV_VALUES, "AI_OPERATION_CONTEXT")
        or "the BlindAssist smart-glasses system with a live camera and GPS"
    ),
    operating_region=(
        _get_config_value(_ENV_VALUES, "AI_OPERATION_REGION") or "Taiwan"
    ),
    response_language=(
        _get_config_value(_ENV_VALUES, "AI_RESPONSE_LANGUAGE")
        or "Traditional Chinese (zh-TW)"
    ),
)
AI_RESPONSE_LANGUAGE = ASSISTANT_CONFIG.response_language


def _normalize_content_type(content_type: str | None) -> str:
    return (content_type or "").split(";", 1)[0].strip().lower()


def _get_stt() -> WhisperSTT:
    global _stt_instance

    if _stt_instance is None:
        with _service_lock:
            if _stt_instance is None:
                from AiServer.speech.stt import WhisperSTT

                logger.info("Initializing Whisper STT service")
                _stt_instance = WhisperSTT()
                logger.info("Whisper STT service initialized")

    return _stt_instance


def _get_tts() -> PiperTTS:
    global _tts_instance

    if _tts_instance is None:
        with _service_lock:
            if _tts_instance is None:
                from AiServer.speech.tts import PiperTTS

                logger.info("Initializing Piper TTS service")
                _tts_instance = PiperTTS()
                logger.info("Piper TTS service initialized")

    return _tts_instance


def _save_audio_request(audio_bytes: bytes, request_dir: Path) -> Path:
    audio_path = request_dir / "question.wav"
    audio_path.write_bytes(audio_bytes)
    return audio_path


def _get_current_location_context() -> str:
    try:
        from Backend.places_server import database

        location = database.get_latest_location()
    except Exception:  # noqa: BLE001
        logger.warning("Could not load current GPS context for AI prompt", exc_info=True)
        return "Current device GPS is unavailable."

    if not location:
        return "Current device GPS is unavailable."

    latitude = float(location["latitude"])
    longitude = float(location["longitude"])
    source = str(location.get("source") or "unknown")
    updated_at = str(location.get("updatedAt") or "unknown")
    return (
        f"Current device GPS: {latitude:.6f}, {longitude:.6f}; "
        f"source: {source}; last update: {updated_at}."
    )


def _build_prompt(question: str) -> str:
    config = ASSISTANT_CONFIG
    return "\n".join(
        [
            "AI IDENTITY",
            f"- Name: {config.name}",
            f"- Role: {config.role}",
            f"- Primary user: {config.audience}",
            "",
            "OPERATING CONTEXT",
            f"- System: {config.operating_context}",
            f"- Region: {config.operating_region}",
            f"- {_get_current_location_context()}",
            (
                "- 此請求所附的最新相機畫面，就是視障使用者目前想詢問的物體或場景；"
                "請將它視為回答問題時最主要的視覺依據。"
            ),
            "",
            "RESPONSIBILITIES",
            f"- Main task: {config.task}.",
            (
                "- 請使用繁體中文詳細回答使用者的問題，通常以三到五個完整句子說明，"
                "不要只給出簡短結論。"
            ),
            (
                "- 請描述畫面中的主要人物或物體、它們的相對位置、周遭環境、"
                "可能影響行走的障礙物，以及能從畫面確認的危險。"
            ),
            "- 若畫面中有明確且緊急的危險，請先提醒危險，再提供其他細節。",
            "",
            "SAFETY AND RESPONSE RULES",
            "- Use only evidence visible in the image or explicitly supplied in this prompt.",
            "- Never invent objects, distances, street conditions, or navigation directions.",
            "- If evidence is unclear or insufficient, say so honestly.",
            "- Do not claim that a path is safe; remind the user to rely on their cane, "
            "guide dog, and real-world safety signals when appropriate.",
            f"- Respond only in {config.response_language}, using natural wording that "
            "is easy to understand when spoken aloud.",
            "",
            f"USER QUESTION: {question.strip()}",
        ]
    )


def _ask_multimodal_model(question: str, image_bytes: bytes) -> str:
    logger.info(
        "Encoding last image for multimodal request | image_size=%s bytes",
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
        "Sending multimodal request to Ollama | model=%s",
        MODEL_NAME,
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

    last_image_bytes = load_last_image_bytes()

    if last_image_bytes is None:
        logger.error("No last image is available for recognize pipeline")
        raise FileNotFoundError(
            "No last image is available yet. Call /api/videoframe first."
        )

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    try:
        with TemporaryDirectory(prefix="recognize_", dir=RUNTIME_DIR) as temp_dir:
            request_dir = Path(temp_dir)
            audio_path = _save_audio_request(audio_bytes, request_dir)

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
            )

            output_path = request_dir / "answer.wav"

            logger.info("Starting Text-to-Speech step")
            generated_audio_path = _get_tts().synthesize(
                answer_text,
                output_path=output_path,
            )
            generated_audio = generated_audio_path.read_bytes()

            logger.info(
                "Recognize pipeline completed successfully | output_size=%s bytes",
                len(generated_audio),
            )
            return generated_audio
    except Exception:
        logger.exception("Recognize pipeline failed")
        raise
