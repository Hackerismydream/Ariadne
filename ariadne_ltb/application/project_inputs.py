from __future__ import annotations

from ariadne_ltb.application.dtos import (
    ProjectInputDetailDTO,
    SourceEvidenceItemDTO,
    SourceLifecycleDTO,
    SourceNextActionDTO,
    SourceTypedArtifactDTO,
)
from ariadne_ltb.application.mappers import source_document_dto
from ariadne_ltb.application.source_understanding import (
    ANALYSIS_LABELS,
    ARTIFACT_LABELS,
    build_source_understandings,
)
from ariadne_ltb.models import SourceArtifact, SourceDocument, SourceEvidence
from ariadne_ltb.storage import AriadneStore


def build_project_inputs(store: AriadneStore) -> list[ProjectInputDetailDTO]:
    understandings = {item.source_id: item for item in build_source_understandings(store)}
    previews = store.list_backlog_previews()
    details: list[ProjectInputDetailDTO] = []
    for source in store.list_source_documents():
        artifacts = store.list_source_artifacts(source.id)
        evidence = store.list_source_evidence(source.id)
        impacted = _impacted_ticket_keys(previews, source, artifacts, evidence)
        details.append(
            ProjectInputDetailDTO(
                source=source_document_dto(store, source),
                lifecycle=_lifecycle(source, artifacts, impacted),
                understanding=understandings.get(source.id),
                artifacts=[_typed_artifact(store, artifact, evidence) for artifact in artifacts],
                evidence=[_evidence_item(item) for item in evidence[:8]],
                impacted_ticket_keys=impacted,
            )
        )
    return details


def _lifecycle(source: SourceDocument, artifacts: list[SourceArtifact], impacted_ticket_keys: list[str]) -> SourceLifecycleDTO:
    status = str(source.metadata.get("analysis_status") or "pending")
    quality_status = str(source.metadata.get("quality_status") or "unknown")
    ready = status in {"analyzed", "partial"} and quality_status != "blocked" and bool(artifacts)
    blocker = str(source.metadata.get("analysis_error") or source.metadata.get("block_reason") or "") or None
    if status in {"blocked", "failed"}:
        detail = blocker or "输入分析失败，需要重新分析或修改来源。"
    elif ready and impacted_ticket_keys:
        detail = f"已影响 {len(impacted_ticket_keys)} 个任务。"
    elif ready:
        detail = "已生成结构化理解，可用于生成任务建议。"
    else:
        detail = "已保存，等待分析或抓取。"
    return SourceLifecycleDTO(
        source_id=source.id,
        status=status,
        label=ANALYSIS_LABELS.get(status, status),
        detail=detail,
        terminal=status in {"analyzed", "partial", "blocked", "failed"},
        ready_for_issue_factory=ready,
        blocker=blocker,
        updated_at=str(source.metadata.get("updated_at") or source.created_at),
        next_actions=_next_actions(status, ready, impacted_ticket_keys),
    )


def _next_actions(status: str, ready: bool, impacted_ticket_keys: list[str]) -> list[SourceNextActionDTO]:
    if status in {"blocked", "failed"}:
        return [
            SourceNextActionDTO(
                id="reanalyze",
                label="重新分析",
                api_action="analyze_source",
            )
        ]
    if ready and impacted_ticket_keys:
        return [
            SourceNextActionDTO(
                id="open_impacted_ticket",
                label=f"打开 {impacted_ticket_keys[0]}",
                target_route=f"#issues/{impacted_ticket_keys[0]}",
            )
        ]
    if ready:
        return [
            SourceNextActionDTO(
                id="generate_issue_delta",
                label="生成任务建议",
                target_route="#plan-changes",
                api_action="issue_factory_preview",
            )
        ]
    return [
        SourceNextActionDTO(
            id="analyze",
            label="分析输入",
            api_action="analyze_source",
        )
    ]


def _typed_artifact(
    store: AriadneStore,
    artifact: SourceArtifact,
    evidence: list[SourceEvidence],
) -> SourceTypedArtifactDTO:
    payload = store.load_source_artifact_payload(artifact.id)
    key_fields: dict[str, object] = {}
    identity = payload.get("identity")
    if isinstance(identity, dict):
        key_fields["commit_sha"] = identity.get("commit_sha")
        key_fields["repo_url"] = identity.get("remote_url") or identity.get("repo_url")
    for key in (
        "manifests",
        "entrypoints",
        "repo_structure",
        "reusable_patterns",
        "risks",
        "avoid_notes",
        "architecture_insights",
        "test_strategy",
        "safety_model",
        "limitations",
        "quality_limitations",
    ):
        value = payload.get(key)
        if isinstance(value, list):
            key_fields[key] = value[:5]
        elif isinstance(value, dict):
            key_fields[key] = value
    quality_status = payload.get("quality_status")
    if isinstance(quality_status, str):
        key_fields["quality_status"] = quality_status
    tests = payload.get("tests")
    if isinstance(tests, dict):
        key_fields["tests"] = tests
    return SourceTypedArtifactDTO(
        id=artifact.id,
        kind=artifact.artifact_type,
        label=ARTIFACT_LABELS.get(artifact.artifact_type, artifact.artifact_type),
        summary=str(payload.get("repo_summary") or payload.get("summary") or artifact.artifact_type),
        payload_path=artifact.payload_path,
        payload_hash=artifact.payload_hash,
        evidence_count=sum(1 for item in evidence if item.artifact_id == artifact.id),
        key_fields={key: value for key, value in key_fields.items() if value is not None},
    )


def _evidence_item(evidence: SourceEvidence) -> SourceEvidenceItemDTO:
    confidence = "高" if evidence.confidence >= 0.75 else "中" if evidence.confidence >= 0.45 else "低"
    return SourceEvidenceItemDTO(
        locator=evidence.locator,
        summary=evidence.quote_or_summary,
        claim=evidence.claim,
        confidence_label=confidence,
    )


def _impacted_ticket_keys(
    previews: object,
    source: SourceDocument,
    artifacts: list[SourceArtifact],
    evidence: list[SourceEvidence],
) -> list[str]:
    source_ids = {source.id}
    artifact_ids = {artifact.id for artifact in artifacts}
    evidence_ids = {item.id for item in evidence}
    keys: list[str] = []
    for preview in previews:  # type: ignore[union-attr]
        for operation in preview.operations:
            metadata = operation.metadata
            if source_ids & set(metadata.get("source_document_ids", [])):
                keys.append(operation.ticket_key or "NEW")
            elif artifact_ids & set(metadata.get("source_artifact_ids", [])):
                keys.append(operation.ticket_key or "NEW")
            elif evidence_ids & set(metadata.get("evidence_refs", [])):
                keys.append(operation.ticket_key or "NEW")
    return sorted(set(keys))[:8]
