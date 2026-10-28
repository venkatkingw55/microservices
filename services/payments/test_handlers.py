"""Tests for the payments service."""

import json
import unittest
import urllib.error
import urllib.request

from services.payments.handlers import build_app
from services.platformhttp.server import start_background, stop_background


class PaymentsTest(unittest.TestCase):
    def setUp(self):
        self.server, self.base = start_background(build_app())
        self.addCleanup(stop_background, self.server)

    def test_authorize_payment(self):
        created = self._request(
            "POST",
            "/v1/payments",
            {"orderId": "order-1", "amountCents": 1999, "currency": "usd"},
        )
        self.assertEqual(created["status"], 201)
        self.assertEqual(created["body"]["currency"], "USD")
        self.assertEqual(created["body"]["status"], "authorized")
        fetched = self._request("GET", f"/v1/payments/{created['body']['id']}")
        self.assertEqual(fetched["body"]["amountCents"], 1999)

    def test_rejects_invalid_amount(self):
        result = self._request(
            "POST",
            "/v1/payments",
            {"orderId": "order-1", "amountCents": -1, "currency": "USD"},
        )
        self.assertEqual(result["status"], 400)

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        data = None if body is None else json.dumps(body).encode()
        headers = {} if data is None else {"Content-Type": "application/json"}
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request) as response:
                return {"status": response.status, "body": json.loads(response.read())}
        except urllib.error.HTTPError as exc:
            return {"status": exc.code, "body": json.loads(exc.read())}
