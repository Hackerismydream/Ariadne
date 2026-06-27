from __future__ import annotations

import operator
from typing import Annotated, Any, NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from ariadne_ltb.application.build_context import IssueFactoryContext
from ariadne_ltb.knowledge.llm_adapter import KnowledgeLLM
from ariadne_ltb.knowledge.models import ContradictionRecord, ProjectPurpose, SourceInsight, SynthesisTheme
from ariadne_ltb.knowledge.nodes.analyze_source import analyze_source
from ariadne_ltb.knowledge.nodes.detect_contradictions import detect_contradictions
from ariadne_ltb.knowledge.nodes.prepare_changes import prepare_changes
from ariadne_ltb.knowledge.nodes.update_themes import update_themes
from ariadne_ltb.knowledge.purpose import project_cycle_id
from ariadne_ltb.knowledge.store import ProjectKnowledgeStore
from ariadne_ltb.storage import AriadneStore


class IngestState(TypedDict):
    project_id: str
    project_purpose: ProjectPurpose
    cycle_id: str
    changed_source_ids: list[str]
    existing_insights: dict[str, SourceInsight]
    existing_themes: list[SynthesisTheme]
    new_insights: Annotated[list[SourceInsight], operator.add]
    updated_themes: list[SynthesisTheme]
    new_contradictions: list[ContradictionRecord]
    current_source_index: int
    source_documents: dict[str, dict[str, Any]]
    source_artifacts: dict[str, list[dict[str, Any]]]
    source_evidence: dict[str, list[dict[str, Any]]]
    node_provenance: Annotated[list[dict[str, Any]], operator.add]
    store: NotRequired[AriadneStore]


def build_ingest_graph(llm: KnowledgeLLM):
    graph = StateGraph(IngestState)
    graph.add_node("prepare_changes", prepare_changes)
    graph.add_node("analyze_source", lambda state: analyze_source(state, llm))
    graph.add_node("update_themes", lambda state: update_themes(state, llm))
    graph.add_node("detect_contradictions", lambda state: detect_contradictions(state, llm))
    graph.add_edge(START, "prepare_changes")
    graph.add_conditional_edges(
        "prepare_changes",
        _next_ingest_step,
        {"analyze_source": "analyze_source", "update_themes": "update_themes"},
    )
    graph.add_conditional_edges(
        "analyze_source",
        _next_ingest_step,
        {"analyze_source": "analyze_source", "update_themes": "update_themes"},
    )
    graph.add_edge("update_themes", "detect_contradictions")
    graph.add_edge("detect_contradictions", END)
    return graph.compile()


def ingest_sources(
    store: AriadneStore,
    *,
    project_id: str,
    purpose: ProjectPurpose,
    context: IssueFactoryContext,
    llm: KnowledgeLLM,
) -> IngestState:
    knowledge_store = ProjectKnowledgeStore(store, project_id)
    existing_insights = knowledge_store.source_insight_by_source_id()
    existing_themes = knowledge_store.list_synthesis_themes()
    cycle_id = project_cycle_id(
        "knowledge_ingest_cycle",
        project_id,
        context.manifest.context_fingerprint,
        len(existing_insights),
    )
    initial_state: IngestState = {
        "project_id": project_id,
        "project_purpose": purpose,
        "cycle_id": cycle_id,
        "changed_source_ids": [],
        "existing_insights": existing_insights,
        "existing_themes": existing_themes,
        "new_insights": [],
        "updated_themes": existing_themes,
        "new_contradictions": [],
        "current_source_index": 0,
        "source_documents": {
            source.id: source.model_dump(mode="json") for source in context.sources
        },
        "source_artifacts": _artifact_payloads_by_source(store, context),
        "source_evidence": _evidence_by_source(context),
        "node_provenance": [],
        "store": store,
    }
    result = build_ingest_graph(llm).invoke(initial_state)
    for insight in result.get("new_insights", []):
        knowledge_store.save_source_insight(SourceInsight.model_validate(insight))
    for theme in result.get("updated_themes", []):
        knowledge_store.save_synthesis_theme(SynthesisTheme.model_validate(theme))
    for contradiction in result.get("new_contradictions", []):
        knowledge_store.save_contradiction(ContradictionRecord.model_validate(contradiction))
    return result


def _next_ingest_step(state: IngestState) -> str:
    return (
        "analyze_source"
        if int(state.get("current_source_index") or 0) < len(state.get("changed_source_ids") or [])
        else "update_themes"
    )


def _artifact_payloads_by_source(
    store: AriadneStore,
    context: IssueFactoryContext,
) -> dict[str, list[dict[str, Any]]]:
    payloads: dict[str, list[dict[str, Any]]] = {}
    for artifact in context.artifacts:
        payload = store.load_source_artifact_payload(artifact.id)
        payloads.setdefault(artifact.source_document_id, []).append(
            {
                "artifact": artifact.model_dump(mode="json"),
                "payload": payload,
            }
        )
    return payloads


def _evidence_by_source(context: IssueFactoryContext) -> dict[str, list[dict[str, Any]]]:
    evidence: dict[str, list[dict[str, Any]]] = {}
    for item in context.evidence:
        evidence.setdefault(item.source_document_id, []).append(item.model_dump(mode="json"))
    return evidence
