"""Payments HTTP API.

This records an authorization decision in memory. It does not call a payment
processor and does not store card or bank details.
"""

from __future__ import annotations

from services.platformhttp.server import Application, Request, Response, Route, created, error, ok
from services.platformhttp.store import MemoryStore, new_id


def build_app(store: MemoryStore | None = None) -> Application:
    payments = store if store is not None else MemoryStore()

    def create_payment(request: Request) -> Response:
        order_id = request.body.get("orderId")
        amount = request.body.get("amountCents")
        currency = request.body.get("currency")
        if not isinstance(order_id, str) or not order_id.strip():
            return error(400, "orderId is required")
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 1:
            return error(400, "amountCents must be a positive integer")
        if not isinstance(currency, str) or len(currency.strip()) != 3 or not currency.isalpha():
            return error(400, "currency must be a 3-letter code")
        record = {
            "id": new_id(),
            "orderId": order_id.strip(),
            "amountCents": amount,
            "currency": currency.strip().upper(),
            "status": "authorized",
        }
        return created(payments.insert(record))

    def get_payment(request: Request) -> Response:
        found = payments.get(request.params["id"])
        if found is None:
            return error(404, "payment not found")
        return ok(found)

    return Application(
        "payments",
        [
            Route("POST", "/v1/payments", create_payment),
            Route("GET", "/v1/payments/{id}", get_payment),
        ],
    )
