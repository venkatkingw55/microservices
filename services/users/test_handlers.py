"""Tests for the users service."""

import json
import unittest
import urllib.error
import urllib.request

from services.platformhttp.server import start_background, stop_background
from services.users.handlers import build_app


class UsersTest(unittest.TestCase):
    def setUp(self):
        self.server, self.base = start_background(build_app())
        self.addCleanup(stop_background, self.server)

    def test_health_and_create_user(self):
        live = self._request("GET", "/health/live")
        self.assertEqual(live["status"], 200)
        ready = self._request("GET", "/health/ready")
        self.assertEqual(ready["status"], 200)

        created = self._request("POST", "/v1/users", {"name": "Ada Lovelace", "email": "ada@example.com"})
        self.assertEqual(created["status"], 201)
        self.assertEqual(created["body"]["email"], "ada@example.com")

        fetched = self._request("GET", f"/v1/users/{created['body']['id']}")
        self.assertEqual(fetched["body"]["name"], "Ada Lovelace")

        listed = self._request("GET", "/v1/users")
        self.assertEqual(len(listed["body"]["items"]), 1)

    def test_duplicate_email_and_validation(self):
        payload = {"name": "Ada", "email": "ada@example.com"}
        self.assertEqual(self._request("POST", "/v1/users", payload)["status"], 201)
        self.assertEqual(self._request("POST", "/v1/users", payload)["status"], 409)
        self.assertEqual(self._request("POST", "/v1/users", {"name": "", "email": "ada@example.com"})["status"], 400)
        self.assertEqual(self._request("GET", "/v1/users/missing")["status"], 404)

    def test_readiness_fails_during_shutdown(self):
        app = build_app()
        server, base = start_background(app)
        self.addCleanup(stop_background, server)
        app.mark_not_ready()
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(base + "/health/ready")
        self.assertEqual(caught.exception.code, 503)
        with urllib.request.urlopen(base + "/health/live") as live:
            self.assertEqual(live.status, 200)

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        data = None if body is None else json.dumps(body).encode()
        headers = {} if data is None else {"Content-Type": "application/json"}
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request) as response:
                raw = response.read()
                parsed = json.loads(raw) if raw else None
                return {"status": response.status, "body": parsed}
        except urllib.error.HTTPError as exc:
            return {"status": exc.code, "body": json.loads(exc.read())}
