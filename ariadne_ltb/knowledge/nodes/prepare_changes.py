from __future__ import annotations

from typing import Any


def prepare_changes(state: dict[str, Any]) -> dict[str, Any]:
    existing = state.get("existing_insights") or {}
    sources = state.get("source_documents") or {}
    changed: list[str] = []
    for source_id, source_data in sources.items():
        prior = existing.get(source_id)
        if prior is None:
            changed.append(source_id)
            continue
        prior_hash = getattr(prior, "source_content_hash", "") or ""
        current_hash = str(source_data.get("content_hash") or "")
        if current_hash and prior_hash and prior_hash != current_hash:
            changed.append(source_id)
    return {"changed_source_ids": changed, "current_source_index": 0}
