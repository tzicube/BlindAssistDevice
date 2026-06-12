from pathlib import Path
from faster_whisper import WhisperModel
from .config import WhisperSTTConfig, SUPPORTED_AUDIO_FORMATS


class WhisperSTT:
    def __init__(self, config: WhisperSTTConfig = WhisperSTTConfig()):
        self.config = config

        self.model = WhisperModel(
            self.config.model_size,
            device=self.config.device,
            compute_type=self.config.compute_type
        )

    def transcribe(self, audio_path: str | Path) -> str:
        audio_path = Path(audio_path)

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if audio_path.suffix.replace(".", "").lower() not in SUPPORTED_AUDIO_FORMATS:
            raise ValueError(
                f"Unsupported audio format: {audio_path.suffix}. "
                f"Supported formats: {SUPPORTED_AUDIO_FORMATS}"
            )

        segments, info = self.model.transcribe(
            str(audio_path),
            language=self.config.language,
            beam_size=int(self.config.beam_size)
        )

        text = " ".join(segment.text.strip() for segment in segments)

        return text.strip()