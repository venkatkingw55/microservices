"""Orders HTTP API."""

from __future__ import annotations

from services.platformhttp.server import Application, Request, Response, Route, created, error, ok
from services.platformhttp.store import MemoryStore, new_id


def build_app(store: MemoryStore | None = None) -> Application:
    orders = store if store is not None else MemoryStore()

    def create_order(request: Request) -> Response:
        user_id = request.body.get("userId")
        sku = request.body.get("sku")
        quantity = request.body.get("quantity")
        if not isinstance(user_id, str) or not user_id.strip():
            return error(400, "userId is required")
        if not isinstance(sku, str) or not sku.strip():
            return error(400, "sku is required")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            return error(400, "quantity must be a positive integer")
        record = {
            "id": new_id(),
            "userId": user_id.strip(),
            "sku": sku.strip(),
            "quantity": quantity,
            "status": "created",
        }
        return created(orders.insert(record))

    def list_orders(_request: Request) -> Response:
        return ok({"items": orders.list()})

    def get_order(request: Request) -> Response:
        found = orders.get(request.params["id"])
        if found is None:
            return error(404, "order not found")
        return ok(found)

    return Application(
        "orders",
        [
            Route("POST", "/v1/orders", create_order),
            Route("GET", "/v1/orders", list_orders),
            Route("GET", "/v1/orders/{id}", get_order),
        ],
    )
