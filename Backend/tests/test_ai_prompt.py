import unittest
from unittest.mock import MagicMock, patch

from AiServer.Recognize import process


class AiPromptTest(unittest.TestCase):
    def test_prompt_defines_identity_task_context_location_and_language(self):
        location = (
            "Current device GPS: 24.990187, 121.343612; "
            "source: test; last update: now."
        )

        with patch.object(process, "_get_current_location_context", return_value=location):
            prompt = process._build_prompt("前面有什麼？")

        self.assertIn("AI IDENTITY", prompt)
        self.assertIn(process.ASSISTANT_CONFIG.name, prompt)
        self.assertIn(process.ASSISTANT_CONFIG.role, prompt)
        self.assertIn(process.ASSISTANT_CONFIG.task, prompt)
        self.assertIn(process.ASSISTANT_CONFIG.operating_region, prompt)
        self.assertIn(location, prompt)
        self.assertIn(process.ASSISTANT_CONFIG.response_language, prompt)
        self.assertIn("就是視障使用者目前想詢問的物體或場景", prompt)
        self.assertIn("三到五個完整句子", prompt)
        self.assertIn("不要只給出簡短結論", prompt)
        self.assertIn("前面有什麼？", prompt)


class OllamaLifecycleTest(unittest.TestCase):
    def test_keep_alive_parser_supports_forever_and_duration_values(self):
        self.assertEqual(-1, process._parse_ollama_keep_alive("-1"))
        self.assertEqual("30m", process._parse_ollama_keep_alive("30m"))

    def test_preload_uses_configured_model_and_infinite_keep_alive(self):
        with (
            patch.object(process, "OLLAMA_KEEP_ALIVE", -1),
            patch.object(process, "_send_ollama_request") as send_request,
        ):
            process.preload_ollama_model()

        payload = send_request.call_args.args[0]
        self.assertEqual(process.MODEL_NAME, payload["model"])
        self.assertEqual("", payload["prompt"])
        self.assertFalse(payload["stream"])
        self.assertEqual(-1, payload["keep_alive"])
        self.assertEqual(
            process.OLLAMA_STARTUP_TIMEOUT_SECONDS,
            send_request.call_args.kwargs["timeout"],
        )

    def test_each_inference_renews_the_configured_keep_alive(self):
        with (
            patch.object(process, "_build_prompt", return_value="test prompt"),
            patch.object(
                process,
                "_send_ollama_request",
                return_value={"response": "test answer"},
            ) as send_request,
        ):
            answer = process._ask_multimodal_model("question", b"image")

        self.assertEqual("test answer", answer)
        payload = send_request.call_args.args[0]
        self.assertEqual(process.OLLAMA_KEEP_ALIVE, payload["keep_alive"])
        self.assertEqual(process.MODEL_NAME, payload["model"])
        self.assertEqual(["aW1hZ2U="], payload["images"])

    def test_shutdown_request_unloads_the_model(self):
        with patch.object(process, "_send_ollama_request") as send_request:
            process.unload_ollama_model()

        payload = send_request.call_args.args[0]
        self.assertEqual(process.MODEL_NAME, payload["model"])
        self.assertEqual(0, payload["keep_alive"])

    def test_stream_sentence_splitter_handles_latin_and_chinese_punctuation(self):
        sentences, remainder = process._extract_complete_sentences(
            "First phrase, 第二段， Third sentence. 第四句。 Remainder"
        )

        self.assertEqual(
            ["First phrase,", "第二段，", "Third sentence.", "第四句。"],
            sentences,
        )
        self.assertEqual("Remainder", remainder)

    def test_ollama_stream_yields_completed_sentence_without_waiting_for_done(self):
        class FakeStreamingResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def __iter__(self):
                return iter(
                    [
                        b'{"response":"Sentence one","done":false}\n',
                        b'{"response":". Sentence","done":false}\n',
                        b'{"response":" two","done":false}\n',
                        b'{"response":".","done":true}\n',
                    ]
                )

        with (
            patch.object(process, "_build_prompt", return_value="test prompt"),
            patch.object(
                process,
                "urlopen",
                return_value=FakeStreamingResponse(),
            ),
        ):
            sentences = list(
                process._stream_multimodal_sentences("question", b"image")
            )

        self.assertEqual(["Sentence one.", "Sentence two."], sentences)

    def test_speech_services_are_preloaded_together(self):
        with (
            patch.object(process, "_get_stt") as get_stt,
            patch.object(process, "_get_tts") as get_tts,
        ):
            process.preload_speech_services()

        get_stt.assert_called_once_with()
        get_tts.assert_called_once_with()

    def test_speech_services_are_closed_and_reset(self):
        tts = MagicMock()
        original_stt = process._stt_instance
        original_tts = process._tts_instance
        process._stt_instance = MagicMock()
        process._tts_instance = tts

        try:
            process.shutdown_speech_services()
            self.assertIsNone(process._stt_instance)
            self.assertIsNone(process._tts_instance)
        finally:
            process._stt_instance = original_stt
            process._tts_instance = original_tts

        tts.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
