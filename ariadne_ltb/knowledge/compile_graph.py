from __future__ import annotations

import operator
from dataclasses import dataclass
from typing import Annotated, Any, NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from ariadne_ltb.application.issue_compiler import CompiledIssueSpec
from ariadne_ltb.knowledge.llm_adapter import KnowledgeLLM
from ariadne_ltb.knowledge.models import (
    BlockerLearning,
    ContradictionRecord,
    OutcomesLog,
    ProjectPurpose,
    SynthesisTheme,
)
from ariadne_ltb.knowledge.nodes.ground_evidence import ground_evidence
from ariadne_ltb.knowledge.nodes.load_knowledge import load_knowledge
from ariadne_ltb.knowledge.nodes.plan_decomposition import plan_decomposition
from ariadne_ltb.knowledge.nodes.quality_gate import quality_gate
from ariadne_ltb.knowledge.nodes.validate_dag import validate_dag
from ariadne_ltb.knowledge.store import ProjectKnowledgeStore
from ariadne_ltb.knowledge.theme_compiler import theme_issue_dicts
from ariadne_ltb.storage import AriadneStore


class CompileState(TypedDict):
    project_id: str
    project_purpose: ProjectPurpose
    themes: list[SynthesisTheme]
    outcomes_log: OutcomesLog
    unresolved_blockers: list[BlockerLearning]
    unresolved_contradictions: list[ContradictionRecord]
    target_project_id: str
    draft_issues: list[dict[str, Any]]
    grounded_issues: list[dict[str, Any]]
    validated_issues: list[dict[str, Any]]
    compiled_specs: list[dict[str, Any]]
    quality_score: float
    quality_issues: list[str]
    compile_attempts: int
    used_fallback: bool
    node_provenance: Annotated[list[dict[str, Any]], operator.add]
    store: NotRequired[AriadneStore]


@dataclass(frozen=True)
class KnowledgeCompileGraphResult:
    specs: list[CompiledIssueSpec]
    node_provenance: list[dict[str, Any]]
    quality_issues: list[str]


def build_compile_graph(llm: KnowledgeLLM):
    graph = StateGraph(CompileState)
    graph.add_node("load_knowledge", load_knowledge)
    graph.add_node("plan_decomposition", lambda state: plan_decomposition(state, llm))
    graph.add_node("ground_evidence", lambda state: ground_evidence(state, llm))
    graph.add_node("validate_dag", validate_dag)
    graph.add_node("quality_gate", lambda state: quality_gate(state, llm))
    graph.add_edge(START, "load_knowledge")
    graph.add_edge("load_knowledge", "plan_decomposition")
    graph.add_edge("plan_decomposition", "ground_evidence")
    graph.add_edge("ground_evidence", "validate_dag")
    graph.add_edge("validate_dag", "quality_gate")
    graph.add_conditional_edges(
        "quality_gate",
        _next_compile_step,
        {"plan_decomposition": "plan_decomposition", "end": END},
    )
    return graph.compile()


def compile_from_knowledge(
    store: AriadneStore,
    *,
    project_id: str,
    target_project_id: str,
    purpose: ProjectPurpose,
    llm: KnowledgeLLM,
) -> list[CompiledIssueSpec]:
    return compile_from_knowledge_with_provenance(
        store,
        project_id=project_id,
        target_project_id=target_project_id,
        purpose=purpose,
        llm=llm,
    ).specs


def compile_from_knowledge_with_provenance(
    store: AriadneStore,
    *,
    project_id: str,
    target_project_id: str,
    purpose: ProjectPurpose,
    llm: KnowledgeLLM,
) -> KnowledgeCompileGraphResult:
    initial_state: CompileState = {
        "project_id": project_id,
        "project_purpose": purpose,
        "themes": [],
        "outcomes_log": OutcomesLog(project_id=project_id),
        "unresolved_blockers": [],
        "unresolved_contradictions": [],
        "target_project_id": target_project_id,
        "draft_issues": [],
        "grounded_issues": [],
        "validated_issues": [],
        "compiled_specs": [],
        "quality_score": 0.0,
        "quality_issues": [],
        "compile_attempts": 0,
        "used_fallback": False,
        "node_provenance": [],
        "store": store,
    }
    result = build_compile_graph(llm).invoke(initial_state)
    return KnowledgeCompileGraphResult(
        specs=[_compiled_issue_spec(item) for item in result.get("compiled_specs", [])],
        node_provenance=[dict(item) for item in result.get("node_provenance", []) if isinstance(item, dict)],
        quality_issues=[str(item) for item in result.get("quality_issues", [])],
    )


def compile_deterministic_from_themes(
    store: AriadneStore,
    *,
    project_id: str,
) -> list[CompiledIssueSpec]:
    themes = ProjectKnowledgeStore(store, project_id).list_synthesis_themes()
    return [_compiled_issue_spec(item) for item in theme_issue_dicts(themes)]


def _next_compile_step(state: CompileState) -> str:
    if state.get("compiled_specs") or int(state.get("compile_attempts") or 0) >= 2:
        return "end"
    return "plan_decomposition"


def _compiled_issue_spec(item: dict[str, Any]) -> CompiledIssueSpec:
    affected_modules = [str(value) for value in item.get("affected_modules", []) if str(value).strip()]
    acceptance_criteria = [
        str(value) for value in item.get("acceptance_criteria", []) if str(value).strip()
    ]
    if not affected_modules:
        affected_modules = ["src/", "tests/"]
    if len(acceptance_criteria) < 2:
        acceptance_criteria.extend(
            [
                "The change is reachable from the Ariadne-managed target project path.",
                "Tests or documented verification cover the completed behavior.",
            ][: 2 - len(acceptance_criteria)]
        )
    return CompiledIssueSpec(
        title=str(item.get("title") or "Untitled issue"),
        reason=str(item.get("reason") or "Generated from ProjectKnowledge."),
        priority=_normalize_priority(str(item.get("priority") or "medium")),
        affected_modules=affected_modules,
        acceptance_criteria=acceptance_criteria,
        evidence_refs=[str(value) for value in item.get("evidence_refs", [])],
        owner_agent=str(item.get("owner_agent") or "Build Lead"),
        build_decision=str(item.get("build_decision") or "code_task"),
        risks=[str(value) for value in item.get("risks", [])],
        assumptions=[str(value) for value in item.get("assumptions", [])],
    )



def _normalize_priority(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"p0", "high"}:
        return "high"
    if normalized in {"p2", "low"}:
        return "low"
    return "medium"
