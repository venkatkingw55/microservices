"""Users HTTP API."""

from __future__ import annotations

from services.platformhttp.server import Application, Request, Response, Route, created, error, ok
from services.platformhttp.store import MemoryStore, new_id


def build_app(store: MemoryStore | None = None) -> Application:
    users = store if store is not None else MemoryStore()

    def create_user(request: Request) -> Response:
        name = request.body.get("name")
        email = request.body.get("email")
        if not isinstance(name, str) or not name.strip():
            return error(400, "name is required")
        if not _valid_email(email):
            return error(400, "email is required")
        record = {"id": new_id(), "name": name.strip(), "email": email.strip().lower()}
        stored = users.insert(record, unique=lambda new, existing: new["email"] == existing["email"])
        if stored is None:
            return error(409, "email already exists")
        return created(stored)

    def list_users(_request: Request) -> Response:
        return ok({"items": users.list()})

    def get_user(request: Request) -> Response:
        found = users.get(request.params["id"])
        if found is None:
            return error(404, "user not found")
        return ok(found)

    return Application(
        "users",
        [
            Route("POST", "/v1/users", create_user),
            Route("GET", "/v1/users", list_users),
            Route("GET", "/v1/users/{id}", get_user),
        ],
    )


def _valid_email(value: object) -> bool:
    if not isinstance(value, str):
        return False
    local, separator, domain = value.strip().partition("@")
    return bool(separator and local and domain and "." in domain)
