import unittest
from unittest.mock import patch

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
        self.assertIn("前面有什麼？", prompt)


if __name__ == "__main__":
    unittest.main()
