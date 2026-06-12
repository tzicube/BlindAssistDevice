from pathlib import Path


SUPPORTED_AUDIO_FORMATS = {"wav"}


class WhisperSTTConfig:
    model_size: str = "large-v3"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str | None = None
    beam_size: int = 2


class PiperTTSConfig:
    model_path: Path = Path(r"C:\Users\Admin\en_US-amy-medium.onnx")
    output_dir: Path = Path("temp_audio")
    audio_format: str = "wav"