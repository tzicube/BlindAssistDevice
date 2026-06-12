from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[3]

DEFAULT_AUDIO_DIR = BASE_DIR / "defaultAudio"

MODE_AUDIO_MAP = {
    "conversation_mode": DEFAULT_AUDIO_DIR / "conversation_mode.wav",
    "conversation": DEFAULT_AUDIO_DIR / "conversation_mode.wav",
    "object_search": DEFAULT_AUDIO_DIR / "objectSearch_mode.wav",
    "mobility_mode": DEFAULT_AUDIO_DIR / "mobility_mode.wav",
    "mobility": DEFAULT_AUDIO_DIR / "mobility_mode.wav",
}


def get_mode_audio(mode: str) -> Path:
    audio_path = MODE_AUDIO_MAP.get(mode)

    if audio_path is None:
        raise ValueError(f"Unsupported mode: {mode}")

    if not audio_path.exists():
        raise FileNotFoundError(audio_path)

    return audio_path
