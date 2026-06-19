from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ariadne_ltb.models import SourceDocument


class SourceAssetView(BaseModel):
    id: str
    kind: str
    source_role: str
    title: str
    uri_or_path: str
    analysis_status: str
    snapshot: dict[str, Any] = Field(default_factory=dict)
    artifact_ids: list[str] = Field(default_factory=list)
    license_risk: str = "unknown"


def source_asset_from_document(source: SourceDocument) -> SourceAssetView:
    metadata = source.metadata or {}
    return SourceAssetView(
        id=source.id,
        kind=source.source_type.value,
        source_role=str(metadata.get("source_role") or _default_source_role(source.source_type.value)),
        title=source.title,
        uri_or_path=source.path_or_url,
        analysis_status=str(metadata.get("analysis_status") or "pending"),
        snapshot=dict(metadata.get("snapshot") or {"content_hash": source.content_hash}),
        artifact_ids=list(metadata.get("artifact_ids") or []),
        license_risk=str(metadata.get("license_risk") or "unknown"),
    )


def _default_source_role(source_type: str) -> str:
    if source_type == "github_repo":
        return "reference_project"
    if source_type == "target_codebase":
        return "target_codebase"
    return "background_knowledge"
