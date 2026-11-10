import os
from pathlib import Path
import subprocess
import uuid

from AiServer.AiConfig import PiperTTSConfig, SUPPORTED_AUDIO_FORMATS


class PiperTTS:
    def __init__(self, config: PiperTTSConfig = PiperTTSConfig()):
        self.config = config

        if not self.config.model_path.exists():
            raise FileNotFoundError(f"Piper model not found: {self.config.model_path}")

        if self.config.audio_format not in SUPPORTED_AUDIO_FORMATS:
            raise ValueError(f"Unsupported audio format: {self.config.audio_format}")

    def synthesize(self, text: str, output_path: str | Path | None = None) -> Path:
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        if output_path is None:
            output_path = self.config.output_dir / f"tts_{uuid.uuid4().hex}.wav"
        else:
            output_path = Path(output_path)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        process_environment = os.environ.copy()
        process_environment["PYTHONIOENCODING"] = "utf-8"
        process_environment["PYTHONUTF8"] = "1"

        result = subprocess.run(
            [
                "piper",
                "--model",
                str(self.config.model_path),
                "--output_file",
                str(output_path)
            ],
            input=text.strip(),
            text=True,
            encoding="utf-8",
            env=process_environment,
            capture_output=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"Piper TTS failed:\n{result.stderr}")

        return output_path
