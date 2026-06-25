from __future__ import annotations

import json
import subprocess
from hashlib import sha256
from pathlib import Path

from ariadne_ltb.application.dtos import ProjectGoalDTO
from ariadne_ltb.application.repository_scanner import scan_repository
from ariadne_ltb.application.source_analysis import SourceAnalysisService
from ariadne_ltb.backlog import ticket_backlog_fingerprint
from ariadne_ltb.models import BuildContextManifest, SourceArtifact, SourceDocument, SourceEvidence, SourceType, stable_id
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
    sources = _with_target_codebase_snapshot_source(store, target_project_id, sources)
    not_ready = [
        source.id
        for source in sources
        if str(source.metadata.get("analysis_status") or "pending") not in {"analyzed", "partial"}
        or not store.list_source_artifacts(source.id)
    ]
    if not_ready:
        msg = f"source_not_ready_for_issue_factory:{','.join(not_ready)}"
        raise ValueError(msg)
    artifacts = [
        artifact
        for source in sources
        for artifact in _current_source_artifacts(store, source)
    ]
    evidence = [
        item
        for source in sources
        for item in store.list_source_evidence(source.id)
    ]
    codebase_snapshot = _current_codebase_snapshot(sources, artifacts)
    snapshot_status, snapshot_reason = _codebase_snapshot_status(codebase_snapshot, sources)
    base_fingerprint = ticket_backlog_fingerprint(store)
    context_payload = {
        "goal_id": goal.id,
        "target_project_id": target_project_id,
        "source_document_ids": sorted(source.id for source in sources),
        "source_artifact_ids": sorted(artifact.id for artifact in artifacts),
        "evidence_ids": sorted(item.id for item in evidence),
        "codebase_snapshot_artifact_id": codebase_snapshot.id if codebase_snapshot else None,
        "codebase_snapshot_status": snapshot_status,
        "codebase_snapshot_reason": snapshot_reason,
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
        codebase_snapshot_status=snapshot_status,
        codebase_snapshot_reason=snapshot_reason,
        base_ticket_fingerprint=base_fingerprint,
        context_fingerprint=context_fingerprint,
    )
    store.save_build_context_manifest(manifest)
    return IssueFactoryContext(manifest=manifest, sources=sources, artifacts=artifacts, evidence=evidence)


def _with_target_codebase_snapshot_source(
    store: AriadneStore,
    target_project_id: str,
    sources: list[SourceDocument],
) -> list[SourceDocument]:
    target_path = _target_project_path(store, target_project_id)
    if target_path is None:
        return sources
    content_hash = _target_codebase_content_hash(target_project_id, target_path)
    existing_target_source = next(
        (
            source
            for source in sources
            if source.source_type is SourceType.TARGET_CODEBASE
            and source.metadata.get("target_project_id") == target_project_id
        ),
        None,
    )
    source_id = existing_target_source.id if existing_target_source else stable_id("source", "target_codebase", target_project_id, target_path)
    try:
        source = store.load_source_document(source_id)
    except FileNotFoundError:
        source = SourceDocument(
            id=source_id,
            source_type=SourceType.TARGET_CODEBASE,
            title=f"Target codebase: {Path(target_path).name}",
            path_or_url=target_path,
            content_hash=content_hash,
            summary=f"Read-only snapshot of target project {target_project_id}.",
            metadata={
                "source_role": "target_codebase",
                "origin_bucket": "target_codebase",
                "target_project_id": target_project_id,
            },
        )
        store.save_source_document(source)
    else:
        if source.content_hash != content_hash:
            source = source.model_copy(
                update={
                    "content_hash": content_hash,
                    "metadata": source.metadata
                    | {
                        "analysis_status": "pending",
                        "snapshot_stale_reason": "target_codebase_changed",
                        "artifact_ids": [],
                    },
                }
            )
            store.save_source_document(source)
    if str(source.metadata.get("analysis_status") or "pending") not in {"analyzed", "partial"} or not store.list_source_artifacts(source.id):
        SourceAnalysisService(store).analyze_source(source.id)
        source = store.load_source_document(source.id)
    replaced = False
    merged: list[SourceDocument] = []
    for existing in sources:
        if existing.source_type is SourceType.TARGET_CODEBASE and existing.id == source.id:
            merged.append(source)
            replaced = True
        elif existing.source_type is SourceType.TARGET_CODEBASE and existing.metadata.get("target_project_id") == target_project_id:
            merged.append(source)
            replaced = True
        else:
            merged.append(existing)
    if not replaced:
        merged.append(source)
    deduped: dict[str, SourceDocument] = {}
    for item in merged:
        deduped[item.id] = item
    return list(deduped.values())


def _target_project_path(store: AriadneStore, target_project_id: str) -> str | None:
    for resource in store.load_project_resources():
        if resource.id != target_project_id:
            continue
        path = resource.resource_ref.get("local_path")
        return str(path) if path else None
    return None


def _target_codebase_content_hash(target_project_id: str, target_path: str) -> str:
    repo_path = Path(target_path).expanduser()
    git_fingerprint = _git_worktree_fingerprint(repo_path) or ""
    directory_fingerprint = _directory_fingerprint(repo_path)
    scan_fingerprint = _scan_fingerprint(repo_path)
    return sha256(
        f"{target_project_id}\n{target_path}\n{git_fingerprint}\n{directory_fingerprint}\n{scan_fingerprint}".encode(
            "utf-8"
        )
    ).hexdigest()


def _git_worktree_fingerprint(repo_path: Path) -> str | None:
    if not (repo_path / ".git").exists():
        return None
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo_path,
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return f"git:{head}\n{status}"


def _directory_fingerprint(repo_path: Path) -> str:
    if not repo_path.exists() or not repo_path.is_dir():
        return "missing"
    entries: list[str] = []
    files = [
        path
        for path in sorted(repo_path.rglob("*"))
        if ".git" not in path.parts and path.is_file()
    ][:500]
    for path in files:
        try:
            stat = path.stat()
        except OSError:
            continue
        entries.append(f"{path.relative_to(repo_path).as_posix()}:{stat.st_mtime_ns}:{stat.st_size}")
    return "\n".join(entries)


def _scan_fingerprint(repo_path: Path) -> str:
    try:
        scan = scan_repository(repo_path)
    except (OSError, FileNotFoundError):
        return "scan_unavailable"
    return json.dumps(
        {
            "top_level": scan.top_level,
            "manifests": scan.manifests,
            "test_paths": scan.test_paths,
            "entrypoints": scan.entrypoints,
            "selected_files": scan.selected_files,
            "summary": scan.summary,
        },
        sort_keys=True,
    )


def _codebase_snapshot_status(
    codebase_snapshot: SourceArtifact | None,
    sources: list[SourceDocument],
) -> tuple[str, str | None]:
    if codebase_snapshot:
        return "present", None
    target_sources = [source for source in sources if source.source_type is SourceType.TARGET_CODEBASE]
    if not target_sources:
        return "missing", "target_codebase_source_missing"
    blocker = target_sources[0].metadata.get("analysis_error") or target_sources[0].metadata.get("block_reason")
    return "blocked", str(blocker or "target_codebase_snapshot_unavailable")


def _current_codebase_snapshot(
    sources: list[SourceDocument],
    artifacts: list[SourceArtifact],
) -> SourceArtifact | None:
    artifact_by_id = {artifact.id: artifact for artifact in artifacts}
    for source in sources:
        if source.source_type is not SourceType.TARGET_CODEBASE:
            continue
        artifact_ids = [str(item) for item in source.metadata.get("artifact_ids", [])]
        for artifact_id in artifact_ids:
            artifact = artifact_by_id.get(artifact_id)
            if artifact and artifact.artifact_type == "codebase_snapshot":
                return artifact
    return next((artifact for artifact in artifacts if artifact.artifact_type == "codebase_snapshot"), None)


def _current_source_artifacts(store: AriadneStore, source: SourceDocument) -> list[SourceArtifact]:
    artifacts = store.list_source_artifacts(source.id)
    if source.source_type is not SourceType.TARGET_CODEBASE:
        return artifacts
    current_ids = {str(item) for item in source.metadata.get("artifact_ids", [])}
    if not current_ids:
        return artifacts
    return [artifact for artifact in artifacts if artifact.id in current_ids]
