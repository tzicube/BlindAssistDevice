import os
import unittest
from unittest.mock import patch

from AiServer.speech import tts


class TTSFactoryTest(unittest.TestCase):
    def test_windows_is_the_default_engine(self):
        sentinel = object()
        with (
            patch.dict(os.environ, {}, clear=False),
            patch.object(tts, "WindowsSapiTTS", return_value=sentinel) as windows_tts,
        ):
            os.environ.pop("TTS_ENGINE", None)
            result = tts.create_tts()

        self.assertIs(result, sentinel)
        windows_tts.assert_called_once_with()

    def test_piper_can_be_selected_as_fallback(self):
        sentinel = object()
        with patch.object(tts, "PiperTTS", return_value=sentinel) as piper_tts:
            result = tts.create_tts("piper")

        self.assertIs(result, sentinel)
        piper_tts.assert_called_once_with()

    def test_unknown_engine_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported TTS_ENGINE"):
            tts.create_tts("unknown")


if __name__ == "__main__":
    unittest.main()
