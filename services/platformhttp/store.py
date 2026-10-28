"""Process-local record store. State is lost when the process exits."""

from __future__ import annotations

import secrets
import threading
from collections.abc import Callable


def new_id() -> str:
    return secrets.token_hex(8)


class MemoryStore:
    def __init__(self):
        self._items: dict[str, dict] = {}
        self._lock = threading.Lock()

    def insert(self, record: dict, unique: Callable[[dict, dict], bool] | None = None) -> dict | None:
        """Store ``record``. Return it, or None when ``unique`` reports a conflict."""
        with self._lock:
            if unique is not None and any(unique(record, existing) for existing in self._items.values()):
                return None
            self._items[record["id"]] = record
            return record

    def get(self, record_id: str) -> dict | None:
        with self._lock:
            found = self._items.get(record_id)
            return None if found is None else dict(found)

    def list(self) -> list[dict]:
        with self._lock:
            return [dict(item) for item in self._items.values()]
