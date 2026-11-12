from pathlib import Path
from threading import Lock
import uuid
import wave

from piper import PiperVoice

from AiServer.AiConfig import PiperTTSConfig, SUPPORTED_AUDIO_FORMATS


class PiperTTS:
    def __init__(self, config: PiperTTSConfig = PiperTTSConfig()):
        self.config = config

        if not self.config.model_path.exists():
            raise FileNotFoundError(f"Piper model not found: {self.config.model_path}")

        if self.config.audio_format not in SUPPORTED_AUDIO_FORMATS:
            raise ValueError(f"Unsupported audio format: {self.config.audio_format}")

        # Keep the ONNX voice loaded instead of starting the Piper CLI and
        # reloading the model for every sentence.
        self._voice = PiperVoice.load(self.config.model_path)
        self._synthesis_lock = Lock()

    def synthesize(self, text: str, output_path: str | Path | None = None) -> Path:
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        if output_path is None:
            output_path = self.config.output_dir / f"tts_{uuid.uuid4().hex}.wav"
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with self._synthesis_lock, wave.open(str(output_path), "wb") as wav_file:
            self._voice.synthesize_wav(text.strip(), wav_file)

        return output_path
