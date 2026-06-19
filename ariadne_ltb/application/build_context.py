from __future__ import annotations

import json
from hashlib import sha256

from ariadne_ltb.application.dtos import ProjectGoalDTO
from ariadne_ltb.backlog import ticket_backlog_fingerprint
from ariadne_ltb.models import BuildContextManifest, SourceArtifact, SourceDocument, SourceEvidence, stable_id
from ariadne_ltb.storage import AriadneStore


class IssueFactoryContext:
    def __init__(
        self,
        *,
        manifest: BuildContextManifest,
        sources: list[SourceDocument],
        artifacts: list[SourceArtifact],
        evidence: list[SourceEvidence],
    ) -> None:
        self.manifest = manifest
        self.sources = sources
        self.artifacts = artifacts
        self.evidence = evidence


def assemble_issue_factory_context(
    store: AriadneStore,
    goal: ProjectGoalDTO,
    sources: list[SourceDocument],
    target_project_id: str | None,
) -> IssueFactoryContext:
    if target_project_id is None:
        msg = "missing_target_project_id"
        raise ValueError(msg)
    artifacts = [
        artifact
        for source in sources
        for artifact in store.list_source_artifacts(source.id)
    ]
    evidence = [
        item
        for source in sources
        for item in store.list_source_evidence(source.id)
    ]
    codebase_snapshot = next(
        (artifact for artifact in artifacts if artifact.artifact_type == "codebase_snapshot"),
        None,
    )
    base_fingerprint = ticket_backlog_fingerprint(store)
    context_payload = {
        "goal_id": goal.id,
        "target_project_id": target_project_id,
        "source_document_ids": sorted(source.id for source in sources),
        "source_artifact_ids": sorted(artifact.id for artifact in artifacts),
        "evidence_ids": sorted(item.id for item in evidence),
        "codebase_snapshot_artifact_id": codebase_snapshot.id if codebase_snapshot else None,
        "base_ticket_fingerprint": base_fingerprint,
    }
    context_fingerprint = sha256(json.dumps(context_payload, sort_keys=True).encode("utf-8")).hexdigest()
    manifest = BuildContextManifest(
        id=stable_id("build_context", context_fingerprint),
        goal_id=goal.id,
        target_project_id=target_project_id,
        source_document_ids=context_payload["source_document_ids"],
        source_artifact_ids=context_payload["source_artifact_ids"],
        evidence_ids=context_payload["evidence_ids"],
        codebase_snapshot_artifact_id=context_payload["codebase_snapshot_artifact_id"],
        base_ticket_fingerprint=base_fingerprint,
        context_fingerprint=context_fingerprint,
    )
    store.save_build_context_manifest(manifest)
    return IssueFactoryContext(manifest=manifest, sources=sources, artifacts=artifacts, evidence=evidence)
