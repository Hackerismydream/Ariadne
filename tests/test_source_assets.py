from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ariadne_ltb.application.source_assets import source_asset_from_document
from ariadne_ltb.models import SourceArtifact, SourceDocument, SourceEvidence, SourceType
from ariadne_ltb.storage import AriadneStore


def test_legacy_source_document_converts_to_source_asset_metadata(tmp_path) -> None:
    store = AriadneStore(tmp_path)
    source = SourceDocument(
        id="src_legacy",
        source_type=SourceType.GITHUB_REPO,
        title="mini-SWE-agent",
        path_or_url="https://github.com/SWE-agent/mini-SWE-agent",
        content_hash="abc123",
        summary="reference repo",
        metadata={},
    )
    store.save_source_document(source)

    asset = source_asset_from_document(store.load_source_document("src_legacy"))

    assert asset.id == "src_legacy"
    assert asset.kind == "github_repo"
    assert asset.source_role == "reference_project"
    assert asset.snapshot["content_hash"] == "abc123"
    assert asset.analysis_status == "pending"


def test_source_evidence_requires_existing_source(tmp_path) -> None:
    store = AriadneStore(tmp_path)
    evidence = SourceEvidence(
        id="ev_missing",
        source_document_id="missing",
        artifact_id=None,
        locator="README.md#L1-L3",
        quote_or_summary="The project exposes a CLI entrypoint.",
        claim="reference repo has a CLI entrypoint",
        confidence=0.8,
        content_hash="sha256:missing",
        created_at=datetime.now(UTC),
    )

    with pytest.raises(ValueError, match="missing_source_document"):
        store.save_source_evidence(evidence)


def test_source_artifact_payload_hash_is_verified(tmp_path) -> None:
    store = AriadneStore(tmp_path)
    source = SourceDocument(
        id="src_note",
        source_type=SourceType.NOTE,
        title="Minimal agent note",
        path_or_url="file://minimal-agent.md",
        content_hash="notehash",
        summary="Minimal agent loop.",
        metadata={},
    )
    store.save_source_document(source)
    artifact = SourceArtifact(
        id="artifact_note",
        source_document_id=source.id,
        artifact_type="knowledge_card",
        payload_hash="",
        payload_path="",
        evidence_ids=[],
        created_at=datetime.now(UTC),
    )

    saved = store.save_source_artifact(artifact, {"summary": "query model then observe"})
    payload_path = store.source_artifact_payload_path(saved.id)
    payload_path.write_text('{"summary":"tampered"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="source_artifact_payload_hash_mismatch"):
        store.load_source_artifact_payload(saved.id)
