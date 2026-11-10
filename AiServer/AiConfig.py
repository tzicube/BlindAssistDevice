import os
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_AUDIO_FORMATS = {"wav"}
BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class AssistantConfig:
    name: str = "BlindAssist"
    role: str = "協助視障者理解視覺資訊與感知周遭環境的人工智慧助理"
    audience: str = "視障或低視力使用者"
    task: str = (
        "將最新的相機畫面視為視障使用者目前想詢問的物體或場景，"
        "分析畫面、回答使用者的語音問題"
        "並優先提醒可能的緊急危險"
    )
    operating_context: str = (
        "配備即時相機與 GPS 的 BlindAssist 智慧眼鏡系統"
    )
    operating_region: str = "臺灣"
    response_language: str = "繁體中文（zh-TW）"


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

