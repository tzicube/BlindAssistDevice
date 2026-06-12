from __future__ import annotations

import base64
import binascii
from pathlib import Path
from typing import Any, Callable

from ai_server.core.speech import transcribe_wav


PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEMP_AUDIO_DIR = PROJECT_ROOT / "temp_audio"


class ConversationPipeline:
    def __init__(self, stt_transcriber: Callable[[str | Path], str] | None = None) -> None:
        self.stt_transcriber = stt_transcriber or transcribe_wav
        self.temp_audio_dir = TEMP_AUDIO_DIR
        self.temp_audio_dir.mkdir(parents=True, exist_ok=True)

    def handle_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        message_type = payload.get("type")
        if message_type == "start_mode":
            return self._handle_start_mode(payload)
        if message_type == "audio_input":
            return self._handle_audio_input(payload)
        raise ValueError(f"Unsupported message type: {message_type}")

    def _handle_start_mode(self, payload: dict[str, Any]) -> dict[str, Any]:
        mode = payload.get("mode")
        if mode != "conversation":
            raise ValueError("Only conversation mode is supported right now.")

        return {
            "type": "mode_started",
            "status": True,
            "mode": "conversation",
            "mode_audio": "conversation_mode.wav",
        }

    def _handle_audio_input(self, payload: dict[str, Any]) -> dict[str, Any]:
        mode = payload.get("mode")
        audio_format = str(payload.get("audio_format", "")).lower()
        audio_data = payload.get("audio_data")

        if mode != "conversation":
            raise ValueError("Audio input is only available for conversation mode.")
        if audio_format != "wav":
            raise ValueError("Only wav audio is supported.")
        if not isinstance(audio_data, str) or not audio_data.strip():
            raise ValueError("audio_data must be a non-empty base64 string.")

        audio_path = self._save_base64_wav(audio_data)
        recognized_text = self.stt_transcriber(audio_path)
        print(f"[Conversation Mode] User said: {recognized_text}", flush=True)

        return {
            "type": "stt_result",
            "status": True,
            "mode": "conversation",
            "recognized_text": recognized_text,
            "language": None,
            "audio_file": str(audio_path.name),
        }

    def _save_base64_wav(self, audio_data: str) -> Path:
        encoded_data = audio_data.split(",", 1)[1] if "," in audio_data else audio_data
        try:
            raw_audio = base64.b64decode(encoded_data, validate=True)
        except binascii.Error as exc:
            raise ValueError("audio_data is not valid base64.") from exc

        if not self._looks_like_wav(raw_audio):
            raise ValueError("Decoded payload is not a valid wav file.")

        output_path = self.temp_audio_dir / "input.wav"
        output_path.write_bytes(raw_audio)
        return output_path

    @staticmethod
    def _looks_like_wav(raw_audio: bytes) -> bool:
        return (
            len(raw_audio) >= 12
            and raw_audio[:4] == b"RIFF"
            and raw_audio[8:12] == b"WAVE"
        )
