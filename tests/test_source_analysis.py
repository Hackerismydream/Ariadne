from __future__ import annotations

from hashlib import sha256

from ariadne_ltb.application.source_analysis import SourceAnalysisService
from ariadne_ltb.models import SourceDocument, SourceType, stable_id
from ariadne_ltb.storage import AriadneStore


def _create_source_document(
    store: AriadneStore,
    *,
    source_type: SourceType,
    title: str,
    path_or_url: str,
    content: str,
    metadata: dict[str, object] | None = None,
) -> SourceDocument:
    source = SourceDocument(
        id=stable_id("source", path_or_url, title, sha256(content.encode("utf-8")).hexdigest()),
        source_type=source_type,
        title=title,
        path_or_url=path_or_url,
        content_hash=sha256((path_or_url + "\n" + content).encode("utf-8")).hexdigest(),
        summary=content[:240] or title,
        metadata=(metadata or {}) | {"content": content},
    )
    store.save_source_document(source)
    return source


def test_markdown_source_analysis_writes_knowledge_card(tmp_path) -> None:
    store = AriadneStore(tmp_path)
    source = _create_source_document(
        store,
        source_type=SourceType.NOTE,
        title="Minimal agent note",
        path_or_url="file://notes/minimal-agent.md",
        content="A minimal agent repeats: query model, parse action, execute, observe.",
        metadata={"source_role": "requirement_source"},
    )

    result = SourceAnalysisService(store).analyze_source(source.id)

    assert result.status == "analyzed"
    artifacts = store.list_source_artifacts(source.id)
    assert artifacts[0].artifact_type == "knowledge_card"
    payload = store.load_source_artifact_payload(artifacts[0].id)
    evidence = store.list_source_evidence(source.id)
    assert "query model" in payload["summary"].lower()
    assert evidence
    assert evidence[0].artifact_id == artifacts[0].id
    assert evidence[0].id in artifacts[0].evidence_ids
    saved_source = store.load_source_document(source.id)
    assert saved_source.metadata["quality_status"] == "usable"
    assert saved_source.metadata["claim_count"] >= 1


def test_raw_html_source_analysis_marks_low_quality(tmp_path) -> None:
    store = AriadneStore(tmp_path)
    source = _create_source_document(
        store,
        source_type=SourceType.BLOG,
        title="Raw shell page",
        path_or_url="https://example.test/app",
        content="<!doctype html><html><head><script>window.x=1</script></head><body><div>Hi</div></body></html>",
        metadata={"source_role": "requirement_source"},
    )

    result = SourceAnalysisService(store).analyze_source(source.id)

    assert result.status == "blocked"
    saved_source = store.load_source_document(source.id)
    assert saved_source.metadata["quality_status"] == "blocked"
    assert "html_extraction_too_short" in saved_source.metadata["quality_limitations"]


def test_github_repo_analysis_writes_repository_understanding(tmp_path) -> None:
    repo = tmp_path / "reference"
    repo.mkdir()
    (repo / "README.md").write_text(
        "# MiniCode\n\nCLI coding assistant with sessions and diff review.",
        encoding="utf-8",
    )
    (repo / "LICENSE").write_text("MIT License", encoding="utf-8")
    (repo / "pyproject.toml").write_text(
        "[project]\nname='minicode'\n[project.scripts]\nminicode='minicode.cli:main'\n",
        encoding="utf-8",
    )
    (repo / "tests").mkdir()
    (repo / "tests" / "test_cli.py").write_text("def test_cli():\n    assert True\n", encoding="utf-8")

    store = AriadneStore(tmp_path / "store")
    source = _create_source_document(
        store,
        source_type=SourceType.GITHUB_REPO,
        title="MiniCode local fixture",
        path_or_url=str(repo),
        content="",
        metadata={"source_role": "reference_project"},
    )

    SourceAnalysisService(store).analyze_source(source.id)

    artifact = store.list_source_artifacts(source.id)[0]
    evidence = store.list_source_evidence(source.id)
    payload = store.load_source_artifact_payload(artifact.id)
    assert artifact.artifact_type == "repository_understanding"
    assert evidence[0].artifact_id == artifact.id
    assert evidence[0].id in artifact.evidence_ids
    assert payload["license"]["detected"] == "MIT"
    assert payload["license_risk"] == "green"
    assert payload["manifests"] == ["pyproject.toml"]
    assert payload["entrypoints"]
    assert payload["repo_structure"]["top_level"]
    assert payload["repo_structure"]["test_files"] == ["tests/test_cli.py"]
    assert payload["tests"]["paths"] == ["tests/test_cli.py"]
    assert payload["behavior_patterns"]
    assert payload["reusable_patterns"]
    assert payload["risks"]
    assert payload["architecture_insights"]
    assert payload["test_strategy"]
    assert payload["safety_model"]
    assert "limitations" in payload
    assert len(evidence) >= 3
