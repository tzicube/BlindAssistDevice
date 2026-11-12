import http.client
import base64
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import unified_server
from Backend.database import BackendDatabase


class UnifiedServerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_database = unified_server.backend_api.database
        self.original_ai_mode = unified_server.AI_MODE
        self.original_mock_reply = unified_server.MOCK_REPLY
        self.original_mock_save = unified_server.MOCK_SAVE_OUTPUT

        database = BackendDatabase(
            Path(self.temp_dir.name) / "test.db",
            legacy_places_path=None,
        )
        database.initialize()
        unified_server.backend_api.database = database
        unified_server.AI_MODE = "mock"
        unified_server.MOCK_REPLY = b"RIFFmockWAVE"
        unified_server.MOCK_SAVE_OUTPUT = False

        self.server = unified_server.ExclusiveThreadingHTTPServer(
            ("127.0.0.1", 0),
            unified_server.UnifiedHandler,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        unified_server.backend_api.database = self.original_database
        unified_server.AI_MODE = self.original_ai_mode
        unified_server.MOCK_REPLY = self.original_mock_reply
        unified_server.MOCK_SAVE_OUTPUT = self.original_mock_save
        self.temp_dir.cleanup()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, response.getheader("Content-Type"), response.read()
        finally:
            connection.close()

    def test_dashboard_and_ai_endpoints_share_one_server(self):
        status, _, _ = self.request("GET", "/api/status")
        self.assertEqual(200, status)

        status, _, _ = self.request("GET", "/api/places")
        self.assertEqual(200, status)

        place_payload = json.dumps(
            {
                "name": "School",
                "address": "1 School Road",
                "lat": 24.98,
                "lng": 121.35,
            }
        ).encode("utf-8")
        status, _, body = self.request(
            "POST",
            "/api/places",
            place_payload,
            {"Content-Type": "application/json"},
        )
        self.assertEqual(201, status)
        self.assertEqual("1 School Road", json.loads(body)["address"])

        frame = b"\xff\xd8test-frame\xff\xd9"
        status, _, _ = self.request(
            "POST",
            "/api/videoframe",
            frame,
            {"Content-Type": "image/jpeg"},
        )
        self.assertEqual(200, status)

        status, content_type, body = self.request("GET", "/api/image")
        self.assertEqual(200, status)
        self.assertEqual("image/jpeg", content_type)
        self.assertEqual(frame, body)

        status, content_type, body = self.request(
            "POST",
            "/api/recognize",
            b"RIFFtestWAVE",
            {"Content-Type": "audio/wav"},
        )
        self.assertEqual(200, status)
        self.assertEqual("audio/wav", content_type)
        self.assertEqual(unified_server.MOCK_REPLY, body)

        status, content_type, body = self.request(
            "POST",
            "/api/recognize",
            b"RIFFtestWAVE",
            {
                "Content-Type": "audio/wav",
                "Accept": "application/x-ndjson, audio/wav",
            },
        )
        self.assertEqual(200, status)
        self.assertTrue(content_type.startswith("application/x-ndjson"))
        stream_events = [json.loads(line) for line in body.splitlines()]
        self.assertEqual("audio", stream_events[0]["type"])
        self.assertEqual(
            unified_server.MOCK_REPLY,
            base64.b64decode(stream_events[0]["audio"]),
        )
        self.assertEqual("done", stream_events[1]["type"])
        self.assertEqual(1, stream_events[1]["sentenceCount"])

        status, _, body = self.request("GET", "/api/health")
        self.assertEqual(200, status)
        self.assertIn(b'"service": "blindassist-unified"', body)
        self.assertIn(
            f'"cameraFps": {unified_server.CAMERA_FPS}'.encode("ascii"),
            body,
        )

    def test_telemetry_updates_dashboard_status(self):
        telemetry_payload = json.dumps(
            {
                "latitude": 24.990782,
                "longitude": 121.346525,
                "address": "桃園市中壢區中大路300號",
                "heading": 45,
                "battery": 82,
                "source": "esp-test",
            },
            ensure_ascii=False,
        ).encode("utf-8")
        status, _, body = self.request(
            "POST",
            "/api/telemetry",
            telemetry_payload,
            {"Content-Type": "application/json"},
        )
        self.assertEqual(200, status)
        telemetry = json.loads(body)["telemetry"]
        self.assertEqual("NE", telemetry["direction"])
        self.assertEqual(82, telemetry["battery"])

        status, _, body = self.request("GET", "/api/status")
        self.assertEqual(200, status)
        dashboard = json.loads(body)
        self.assertTrue(dashboard["online"])
        self.assertEqual("桃園市中壢區中大路300號", dashboard["address"])
        self.assertEqual(45, dashboard["heading"])
        self.assertEqual("NE", dashboard["direction"])
        self.assertEqual(82, dashboard["battery"])
        self.assertEqual("NE", dashboard["navigation"]["direction"])

    def test_telemetry_rejects_invalid_battery(self):
        payload = json.dumps(
            {
                "latitude": 24.99,
                "longitude": 121.34,
                "address": "桃園市",
                "heading": 0,
                "battery": 101,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        status, _, body = self.request(
            "POST",
            "/api/telemetry",
            payload,
            {"Content-Type": "application/json"},
        )
        self.assertEqual(400, status)
        self.assertIn(b"battery", body)

    def test_caution_event_is_exposed_to_dashboard(self):
        caution_payload = {
            "event": "fall",
            "message": "使用者可能跌倒",
            "sizeG": 0.85,
            "time": 1763000000000,
            "latitude": 24.990782,
            "longitude": 121.346525,
            "heading": 92.0,
            "direction": "東",
            "source": "android-app",
            "sensor": "esp32",
        }
        status, content_type, body = self.request(
            "POST",
            "/api/caution",
            json.dumps(caution_payload, ensure_ascii=False).encode("utf-8"),
            {"Content-Type": "application/json"},
        )

        self.assertEqual(202, status)
        self.assertTrue(content_type.startswith("application/json"))
        accepted = json.loads(body)["caution"]
        self.assertEqual("fall:1763000000000:android-app:esp32", accepted["id"])
        self.assertEqual("使用者可能跌倒", accepted["message"])

        status, _, body = self.request("GET", "/api/status")
        self.assertEqual(200, status)
        dashboard = json.loads(body)
        self.assertEqual(accepted, dashboard["caution"])

        status, _, body = self.request("GET", "/api/caution")
        self.assertEqual(200, status)
        self.assertEqual(accepted, json.loads(body)["caution"])

    def test_ip_caution_alias_and_validation(self):
        caution_payload = {
            "event": "fall",
            "message": "使用者可能跌倒",
            "sizeG": 0.85,
            "time": 1763000000001,
            "latitude": 24.990782,
            "longitude": 121.346525,
            "heading": 92.0,
            "direction": "東",
            "source": "android-app",
            "sensor": "esp32",
        }
        status, _, _ = self.request(
            "POST",
            "/ip/caution",
            json.dumps(caution_payload, ensure_ascii=False).encode("utf-8"),
            {"Content-Type": "application/json"},
        )
        self.assertEqual(202, status)

        caution_payload.pop("message")
        status, _, body = self.request(
            "POST",
            "/api/caution",
            json.dumps(caution_payload).encode("utf-8"),
            {"Content-Type": "application/json"},
        )
        self.assertEqual(400, status)
        self.assertIn(b"message", body)

    def test_resolves_saved_place_alias_and_returns_not_found(self):
        place_payload = json.dumps(
            {
                "name": "Home",
                "address": "1 Home Road",
                "lat": 24.98,
                "lng": 121.35,
                "aliases": ["家", "回家", "my home"],
            },
            ensure_ascii=False,
        ).encode("utf-8")
        status, _, body = self.request(
            "POST",
            "/api/places",
            place_payload,
            {"Content-Type": "application/json"},
        )
        self.assertEqual(201, status)
        created = json.loads(body)
        self.assertEqual(["家", "回家", "my home"], created["aliases"])

        resolve_payload = json.dumps(
            {"utterance": "帶我回家", "language": "zh-TW"},
            ensure_ascii=False,
        ).encode("utf-8")
        status, _, body = self.request(
            "POST",
            "/api/navigation/resolve",
            resolve_payload,
            {"Content-Type": "application/json"},
        )
        self.assertEqual(200, status)
        resolved = json.loads(body)
        self.assertEqual("saved_place", resolved["matchType"])
        self.assertEqual(created["id"], resolved["destination"]["id"])
        self.assertEqual("回家", resolved["matchedText"])

        missing_payload = json.dumps(
            {"utterance": "導航到 Taipei 101", "language": "zh-TW"},
            ensure_ascii=False,
        ).encode("utf-8")
        status, _, body = self.request(
            "POST",
            "/api/navigation/resolve",
            missing_payload,
            {"Content-Type": "application/json"},
        )
        self.assertEqual(200, status)
        missing = json.loads(body)
        self.assertEqual("not_found", missing["matchType"])
        self.assertEqual("taipei 101", missing["query"])
        self.assertIsNone(missing["destination"])

    def test_resolver_returns_ambiguous_for_shared_alias(self):
        for name, latitude in (("School North", 24.98), ("School South", 24.99)):
            payload = json.dumps(
                {
                    "name": name,
                    "address": f"{name} Road",
                    "lat": latitude,
                    "lng": 121.35,
                    "aliases": ["學校"],
                },
                ensure_ascii=False,
            ).encode("utf-8")
            status, _, _ = self.request(
                "POST",
                "/api/places",
                payload,
                {"Content-Type": "application/json"},
            )
            self.assertEqual(201, status)

        resolve_payload = json.dumps(
            {"utterance": "去學校", "language": "zh-TW"},
            ensure_ascii=False,
        ).encode("utf-8")
        status, _, body = self.request(
            "POST",
            "/api/navigation/resolve",
            resolve_payload,
            {"Content-Type": "application/json"},
        )
        self.assertEqual(200, status)
        result = json.loads(body)
        self.assertEqual("ambiguous", result["matchType"])
        self.assertEqual(2, len(result["candidates"]))

    def test_replaces_aliases_and_validates_resolve_request(self):
        payload = json.dumps(
            {
                "name": "School",
                "address": "1 School Road",
                "lat": 24.98,
                "lng": 121.35,
            }
        ).encode("utf-8")
        status, _, body = self.request(
            "POST",
            "/api/places",
            payload,
            {"Content-Type": "application/json"},
        )
        self.assertEqual(201, status)
        place_id = json.loads(body)["id"]

        status, _, body = self.request(
            "PUT",
            f"/api/places/{place_id}/aliases",
            json.dumps({"aliases": ["學校", "school"]}, ensure_ascii=False).encode(
                "utf-8"
            ),
            {"Content-Type": "application/json"},
        )
        self.assertEqual(200, status)
        self.assertEqual(["學校", "school"], json.loads(body)["aliases"])

        status, _, body = self.request(
            "POST",
            "/api/navigation/resolve",
            json.dumps(
                {"utterance": "Navigate to School", "language": "en-US"}
            ).encode("utf-8"),
            {"Content-Type": "application/json"},
        )
        self.assertEqual(200, status)
        self.assertEqual("saved_place", json.loads(body)["matchType"])

        status, _, body = self.request(
            "POST",
            "/api/navigation/resolve",
            json.dumps({"utterance": "Navigate to"}).encode("utf-8"),
            {"Content-Type": "application/json"},
        )
        self.assertEqual(400, status)
        self.assertIn(b"destination", body)

        status, _, body = self.request(
            "POST",
            "/api/navigation/resolve",
            json.dumps(
                {"utterance": "Navigate to School", "language": "vi-VN"}
            ).encode("utf-8"),
            {"Content-Type": "application/json"},
        )
        self.assertEqual(400, status)
        self.assertIn(b"English or Chinese", body)


class UnifiedServerLifecycleTest(unittest.TestCase):
    def test_real_server_preloads_and_unloads_ollama_model(self):
        from AiServer.Recognize import process as recognize_process

        server = MagicMock()
        server.serve_forever.side_effect = KeyboardInterrupt
        original_ai_mode = unified_server.AI_MODE
        unified_server.AI_MODE = "real"

        try:
            with (
                patch("sys.argv", ["unified_server.py"]),
                patch.object(unified_server.backend_api.database, "initialize"),
                patch.object(
                    unified_server,
                    "ExclusiveThreadingHTTPServer",
                    return_value=server,
                ),
                patch.object(recognize_process, "preload_ollama_model") as preload,
                patch.object(recognize_process, "preload_speech_services") as speech,
                patch.object(recognize_process, "shutdown_speech_services") as shutdown,
                patch.object(recognize_process, "unload_ollama_model") as unload,
            ):
                exit_code = unified_server.main()
        finally:
            unified_server.AI_MODE = original_ai_mode

        self.assertEqual(0, exit_code)
        preload.assert_called_once_with()
        speech.assert_called_once_with()
        shutdown.assert_called_once_with()
        unload.assert_called_once_with()
        server.serve_forever.assert_called_once_with()
        server.server_close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
