from __future__ import annotations

from pathlib import Path
from typing import Any

from ariadne_ltb.application.build_context import IssueFactoryContext
from ariadne_ltb.knowledge.ingest_graph import ingest_sources
from ariadne_ltb.knowledge.models import ProjectPurpose
from ariadne_ltb.knowledge.store import ProjectKnowledgeStore
from ariadne_ltb.models import BuildContextManifest, SourceDocument, SourceType, stable_id
from ariadne_ltb.storage import AriadneStore


class FakeKnowledgeLLM:
    def complete_json(self, prompt: str, schema_name: str) -> dict[str, Any]:
        if schema_name == "SourceInsightDraft":
            return {
                "summary": "Repo shows a compact action loop.",
                "key_claims": [{"claim": "Use action loop", "locator": "README.md", "confidence": 0.8}],
                "reusable_patterns": ["action-observation loop"],
                "risks": ["tool safety"],
            }
        if schema_name == "SynthesisThemeDrafts":
            return {
                "themes": [
                    {
                        "label": "Agent loop",
                        "contributing_source_ids": ["source_1"],
                        "claims": ["Use action loop"],
                        "priority_signal": "high",
                        "affected_modules": ["mini_code_agent/agent_loop.py"],
                    }
                ]
            }
        if schema_name == "ContradictionDrafts":
            return {"contradictions": []}
        raise AssertionError(schema_name)


def test_ingest_graph_persists_only_new_source_insight(tmp_path: Path) -> None:
    store, context = _source_context(tmp_path)
    purpose = ProjectPurpose(project_id="project_1", title="Project", one_line="Build")

    result = ingest_sources(store, project_id="project_1", purpose=purpose, context=context, llm=FakeKnowledgeLLM())

    knowledge = ProjectKnowledgeStore(store, "project_1")
    assert result["changed_source_ids"] == ["source_1"]
    assert knowledge.list_source_insights()[0].summary == "Repo shows a compact action loop."
    assert knowledge.list_synthesis_themes()[0].label == "Agent loop"

    second = ingest_sources(store, project_id="project_1", purpose=purpose, context=context, llm=FakeKnowledgeLLM())
    assert second["changed_source_ids"] == []
    assert len(knowledge.list_source_insights()) == 1


def test_ingest_graph_re_runs_when_source_content_hash_changes(tmp_path: Path) -> None:
    store, context = _source_context(tmp_path)
    purpose = ProjectPurpose(project_id="project_1", title="Project", one_line="Build")
    knowledge = ProjectKnowledgeStore(store, "project_1")

    ingest_sources(store, project_id="project_1", purpose=purpose, context=context, llm=FakeKnowledgeLLM())
    first = knowledge.source_insight_by_source_id()["source_1"]
    assert first.revision == 1
    assert first.source_content_hash == "hash"

    source = store.load_source_document("source_1")
    updated_source = source.model_copy(update={"content_hash": "hash-2"})
    store.save_source_document(updated_source)
    updated_context = IssueFactoryContext(
        manifest=context.manifest,
        sources=[updated_source],
        artifacts=context.artifacts,
        evidence=context.evidence,
    )

    result = ingest_sources(
        store,
        project_id="project_1",
        purpose=purpose,
        context=updated_context,
        llm=FakeKnowledgeLLM(),
    )

    second = knowledge.source_insight_by_source_id()["source_1"]
    assert result["changed_source_ids"] == ["source_1"]
    assert second.revision == 2
    assert second.source_content_hash == "hash-2"


def _source_context(tmp_path: Path) -> tuple[AriadneStore, IssueFactoryContext]:
    store = AriadneStore(tmp_path)
    source = SourceDocument(
        id="source_1",
        source_type=SourceType.GITHUB_REPO,
        title="Reference",
        path_or_url="https://example.com/repo",
        content_hash="hash",
        summary="Reference repo",
        metadata={"analysis_status": "analyzed"},
    )
    store.save_source_document(source)
    manifest = BuildContextManifest(
        id=stable_id("ctx", "1"),
        goal_id="goal_1",
        target_project_id="project_1",
        source_document_ids=[source.id],
        source_artifact_ids=[],
        evidence_ids=[],
        base_ticket_fingerprint="base",
        context_fingerprint="context",
    )
    return store, IssueFactoryContext(manifest=manifest, sources=[source], artifacts=[], evidence=[])
