from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ariadne_ltb.models import utc_now
from ariadne_ltb.storage import AriadneStore


class IdempotencyStore:
    def __init__(self, store: AriadneStore) -> None:
        self.base = store.base / "application" / "idempotency"
        self.base.mkdir(parents=True, exist_ok=True)

    def get(self, key: str | None, action: str = "default") -> dict[str, Any] | None:
        if not key:
            return None
        path = self._path(action, key)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("response")

    def set(self, key: str | None, value: dict[str, Any], action: str = "default") -> None:
        if not key:
            return
        path = self._path(action, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "action": action,
            "idempotency_key": key,
            "response": value,
            "created_at": utc_now(),
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _path(self, action: str, key: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", key):
            msg = "invalid idempotency key"
            raise ValueError(msg)
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", action):
            msg = "invalid idempotency action"
            raise ValueError(msg)
        return self.base / action / f"{key}.json"


class MutationIdempotencyStore:
    def __init__(self, root: Path) -> None:
        self.store = IdempotencyStore.__new__(IdempotencyStore)
        self.store.base = Path(root).resolve() / ".ariadne" / "application" / "idempotency"
        self.store.base.mkdir(parents=True, exist_ok=True)

    def get(self, action: str, key: str) -> dict[str, Any] | None:
        path = self.store._path(action, key)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def record_success(self, action: str, key: str, response: dict[str, Any]) -> None:
        self.store.set(key, response, action)
