import os
from pathlib import Path

SUPPORTED_AUDIO_FORMATS = {"wav"}


class WhisperSTTConfig:
    model_size: str = "medium"
    device: str = "cuda"
    compute_type: str = "float16"
    language: str | None = "en"
    beam_size: int = 5


class PiperTTSConfig:
    model_path: Path = Path(r"C:\Users\Admin\en_US-amy-medium.onnx")
    output_dir: Path = Path("temp_audio")
    audio_format: str = "wav"


class GemmaVisionConfig:
    request_timeout_seconds: int = 30
    system_prompt: str = (
        "You are an assistant supporting blind people. "
    )
    response_instruction: str = (
        "Answer clearly, naturally, and briefly. "
        "If the image does not provide enough evidence, say that honestly."
    )
    question_prefix: str = "Blind user asks:"

