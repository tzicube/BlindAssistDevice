import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
