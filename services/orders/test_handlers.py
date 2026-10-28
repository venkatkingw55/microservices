"""Tests for the orders service."""

import json
import unittest
import urllib.error
import urllib.request

from services.platformhttp.server import start_background, stop_background
from services.orders.handlers import build_app


class OrdersTest(unittest.TestCase):
    def setUp(self):
        self.server, self.base = start_background(build_app())
        self.addCleanup(stop_background, self.server)

    def test_create_and_fetch_order(self):
        created = self._request(
            "POST",
            "/v1/orders",
            {"userId": "user-1", "sku": "WIDGET", "quantity": 2},
        )
        self.assertEqual(created["status"], 201)
        self.assertEqual(created["body"]["status"], "created")
        fetched = self._request("GET", f"/v1/orders/{created['body']['id']}")
        self.assertEqual(fetched["body"]["quantity"], 2)
        self.assertEqual(self._request("GET", "/health/startup")["status"], 200)

    def test_rejects_invalid_quantity(self):
        result = self._request("POST", "/v1/orders", {"userId": "user-1", "sku": "WIDGET", "quantity": 0})
        self.assertEqual(result["status"], 400)
        self.assertEqual(self._request("GET", "/v1/orders/missing")["status"], 404)

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        data = None if body is None else json.dumps(body).encode()
        headers = {} if data is None else {"Content-Type": "application/json"}
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request) as response:
                return {"status": response.status, "body": json.loads(response.read())}
        except urllib.error.HTTPError as exc:
            return {"status": exc.code, "body": json.loads(exc.read())}
