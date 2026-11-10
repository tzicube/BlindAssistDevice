import os
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_AUDIO_FORMATS = {"wav"}
BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class AssistantConfig:
    name: str = "BlindAssist"
    role: str = "assistive visual and situational-awareness AI"
    audience: str = "a blind or low-vision user"
    task: str = (
        "analyze the latest camera image, answer the user's spoken question, "
        "identify relevant objects or obstacles, and prioritize urgent hazards"
        "do not repeat the user's question"
        "When responding, there is no need to introduce who you are."
    )
    operating_context: str = (
        "the BlindAssist smart-glasses system with a live camera and GPS"
    )
    operating_region: str = "Taiwan"
    response_language: str = "Traditional Chinese (zh-TW)"


@dataclass(frozen=True)
class WhisperSTTConfig:
    model_size: str = os.getenv("WHISPER_MODEL_SIZE", "medium")
    device: str = os.getenv("WHISPER_DEVICE", "cuda")
    compute_type: str = os.getenv("WHISPER_COMPUTE_TYPE", "float16")
    language: str | None = os.getenv("WHISPER_LANGUAGE", "zh") or None
    beam_size: int = int(os.getenv("WHISPER_BEAM_SIZE", "5"))


@dataclass(frozen=True)
class PiperTTSConfig:
    model_path: Path = Path(
        os.getenv(
            "PIPER_MODEL_PATH",
            str(BASE_DIR / "models" / "zh_CN-huayan-medium.onnx"),
        )
    ).expanduser()
    output_dir: Path = BASE_DIR / "runtime" / "tts"
    audio_format: str = "wav"

