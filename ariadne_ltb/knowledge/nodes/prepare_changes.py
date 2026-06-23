from __future__ import annotations

from typing import Any


def prepare_changes(state: dict[str, Any]) -> dict[str, Any]:
    existing = state.get("existing_insights") or {}
    source_ids = list(state.get("source_documents", {}).keys())
    changed = [source_id for source_id in source_ids if source_id not in existing]
    return {"changed_source_ids": changed, "current_source_index": 0}

