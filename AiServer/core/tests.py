from django.test import TestCase


class HealthCheckTests(TestCase):
    def test_health_endpoint_returns_ok(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
