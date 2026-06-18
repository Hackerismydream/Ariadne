from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ariadne_ltb.models import utc_now
from ariadne_ltb.storage import AriadneStore


class IdempotencyStore:
    def __init__(self, store: AriadneStore) -> None:
        self.path = store.base / "idempotency" / "keys.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def get(self, key: str | None) -> dict[str, Any] | None:
        if not key or not self.path.exists():
            return None
        return self._read().get(key)

    def set(self, key: str | None, value: dict[str, Any]) -> None:
        if not key:
            return
        values = self._read()
        values[key] = value | {"created_at": utc_now()}
        self.path.write_text(json.dumps(values, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _read(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(Path(self.path).read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}
