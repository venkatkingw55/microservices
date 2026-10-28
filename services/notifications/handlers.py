"""Notifications HTTP API.

Messages are queued in memory. Nothing is delivered to an external provider.
"""

from __future__ import annotations

from services.platformhttp.server import Application, Request, Response, Route, created, error, ok
from services.platformhttp.store import MemoryStore, new_id

CHANNELS = {"email", "sms"}
MAX_MESSAGE_LENGTH = 2000


def build_app(store: MemoryStore | None = None) -> Application:
    notifications = store if store is not None else MemoryStore()

    def create_notification(request: Request) -> Response:
        user_id = request.body.get("userId")
        channel = request.body.get("channel")
        message = request.body.get("message")
        if not isinstance(user_id, str) or not user_id.strip():
            return error(400, "userId is required")
        if not isinstance(channel, str) or channel.strip().lower() not in CHANNELS:
            return error(400, "channel must be email or sms")
        if not isinstance(message, str) or not message.strip():
            return error(400, "message is required")
        if len(message) > MAX_MESSAGE_LENGTH:
            return error(400, "message is too long")
        record = {
            "id": new_id(),
            "userId": user_id.strip(),
            "channel": channel.strip().lower(),
            "message": message.strip(),
            "status": "queued",
        }
        return created(notifications.insert(record))

    def get_notification(request: Request) -> Response:
        found = notifications.get(request.params["id"])
        if found is None:
            return error(404, "notification not found")
        return ok(found)

    return Application(
        "notifications",
        [
            Route("POST", "/v1/notifications", create_notification),
            Route("GET", "/v1/notifications/{id}", get_notification),
        ],
    )
