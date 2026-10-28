"""Tests for the notifications service."""

import json
import unittest
import urllib.error
import urllib.request

from services.notifications.handlers import build_app
from services.platformhttp.server import start_background, stop_background


class NotificationsTest(unittest.TestCase):
    def setUp(self):
        self.server, self.base = start_background(build_app())
        self.addCleanup(stop_background, self.server)

    def test_queue_notification(self):
        created = self._request(
            "POST",
            "/v1/notifications",
            {"userId": "user-1", "channel": "email", "message": "Order shipped"},
        )
        self.assertEqual(created["status"], 201)
        self.assertEqual(created["body"]["status"], "queued")
        fetched = self._request("GET", f"/v1/notifications/{created['body']['id']}")
        self.assertEqual(fetched["body"]["channel"], "email")

    def test_rejects_unknown_channel(self):
        result = self._request(
            "POST",
            "/v1/notifications",
            {"userId": "user-1", "channel": "pager", "message": "hello"},
        )
        self.assertEqual(result["status"], 400)
        with urllib.request.urlopen(self.base + "/metrics") as metrics:
            self.assertIn(b"http_requests_total", metrics.read())

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        data = None if body is None else json.dumps(body).encode()
        headers = {} if data is None else {"Content-Type": "application/json"}
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request) as response:
                return {"status": response.status, "body": json.loads(response.read())}
        except urllib.error.HTTPError as exc:
            return {"status": exc.code, "body": json.loads(exc.read())}
