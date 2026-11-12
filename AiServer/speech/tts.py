from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
from queue import Queue
from threading import Event, Lock, Thread
from typing import Protocol
import uuid
import wave

from AiServer.AiConfig import (
    PiperTTSConfig,
    SUPPORTED_AUDIO_FORMATS,
    WindowsTTSConfig,
)


class TextToSpeech(Protocol):
    def synthesize(self, text: str, output_path: str | Path | None = None) -> Path:
        ...

    def close(self) -> None:
        ...


@dataclass
class _SapiSynthesisRequest:
    text: str
    output_path: Path
    done: Event = field(default_factory=Event)
    error: BaseException | None = None


class WindowsSapiTTS:
    """Persistent local Windows SAPI worker for low-latency WAV synthesis."""

    _SSFM_CREATE_FOR_WRITE = 3
    _SAFT_22KHZ_16BIT_MONO = 22

    def __init__(self, config: WindowsTTSConfig = WindowsTTSConfig()):
        if os.name != "nt":
            raise RuntimeError("Windows SAPI TTS is only available on Windows")
        if config.audio_format not in SUPPORTED_AUDIO_FORMATS:
            raise ValueError(f"Unsupported audio format: {config.audio_format}")
        if not -10 <= config.rate <= 10:
            raise ValueError("WINDOWS_TTS_RATE must be between -10 and 10")
        if not 0 <= config.volume <= 100:
            raise ValueError("WINDOWS_TTS_VOLUME must be between 0 and 100")

        self.config = config
        self._requests: Queue[_SapiSynthesisRequest | None] = Queue()
        self._ready = Event()
        self._startup_error: BaseException | None = None
        self._closed = False
        self._worker = Thread(
            target=self._run_worker,
            name="blindassist-windows-sapi-tts",
            daemon=True,
        )
        self._worker.start()
        if not self._ready.wait(timeout=self.config.timeout_seconds):
            raise TimeoutError("Windows SAPI TTS initialization timed out")
        if self._startup_error is not None:
            raise RuntimeError(
                "Windows SAPI TTS initialization failed"
            ) from self._startup_error

    @staticmethod
    def _find_voice_token(voice, requested_name: str):
        voices = voice.GetVoices()
        available = [voices.Item(index) for index in range(voices.Count)]
        requested = requested_name.strip().casefold()

        for token in available:
            if token.GetDescription().strip().casefold() == requested:
                return token
        for token in available:
            if requested in token.GetDescription().strip().casefold():
                return token

        descriptions = ", ".join(token.GetDescription() for token in available)
        raise RuntimeError(
            f"Windows TTS voice not found: {requested_name}. Available voices: {descriptions}"
        )

    def _run_worker(self) -> None:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        voice = None
        try:
            voice = win32com.client.Dispatch("SAPI.SpVoice")
            voice.Voice = self._find_voice_token(voice, self.config.voice_name)
            voice.Rate = self.config.rate
            voice.Volume = self.config.volume
        except BaseException as error:  # noqa: BLE001
            self._startup_error = error
            self._ready.set()
            pythoncom.CoUninitialize()
            return

        self._ready.set()
        try:
            while True:
                request = self._requests.get()
                if request is None:
                    return

                stream = None
                try:
                    request.output_path.parent.mkdir(parents=True, exist_ok=True)
                    stream = win32com.client.Dispatch("SAPI.SpFileStream")
                    stream.Format.Type = self._SAFT_22KHZ_16BIT_MONO
                    stream.Open(
                        str(request.output_path.resolve()),
                        self._SSFM_CREATE_FOR_WRITE,
                        False,
                    )
                    voice.AudioOutputStream = stream
                    voice.Speak(request.text)
                    stream.Close()
                    stream = None
                except BaseException as error:  # noqa: BLE001
                    request.error = error
                    if stream is not None:
                        try:
                            stream.Close()
                        except Exception:  # noqa: BLE001
                            pass
                    request.output_path.unlink(missing_ok=True)
                finally:
                    request.done.set()
        finally:
            voice = None
            pythoncom.CoUninitialize()

    def synthesize(self, text: str, output_path: str | Path | None = None) -> Path:
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        if self._closed:
            raise RuntimeError("Windows SAPI TTS has already been closed")

        if output_path is None:
            output_path = self.config.output_dir / f"tts_{uuid.uuid4().hex}.wav"
        else:
            output_path = Path(output_path)

        request = _SapiSynthesisRequest(text=text.strip(), output_path=output_path)
        self._requests.put(request)
        if not request.done.wait(timeout=self.config.timeout_seconds):
            raise TimeoutError("Windows SAPI TTS synthesis timed out")
        if request.error is not None:
            raise RuntimeError("Windows SAPI TTS synthesis failed") from request.error
        return output_path

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._requests.put(None)
        self._worker.join(timeout=self.config.timeout_seconds)

    def __enter__(self) -> WindowsSapiTTS:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


class PiperTTS:
    def __init__(self, config: PiperTTSConfig = PiperTTSConfig()):
        self.config = config

        if not self.config.model_path.exists():
            raise FileNotFoundError(f"Piper model not found: {self.config.model_path}")

        if self.config.audio_format not in SUPPORTED_AUDIO_FORMATS:
            raise ValueError(f"Unsupported audio format: {self.config.audio_format}")

        from piper import PiperVoice

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

    def close(self) -> None:
        """Piper has no explicit shutdown operation."""


def create_tts(engine: str | None = None) -> TextToSpeech:
    selected_engine = (engine or os.getenv("TTS_ENGINE", "windows")).strip().lower()
    if selected_engine in {"windows", "sapi", "windows-sapi"}:
        return WindowsSapiTTS()
    if selected_engine == "piper":
        return PiperTTS()
    raise ValueError(
        f"Unsupported TTS_ENGINE: {selected_engine}. Use 'windows' or 'piper'."
    )
