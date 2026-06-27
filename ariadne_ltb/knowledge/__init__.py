from __future__ import annotations

from dataclasses import dataclass, field

from ariadne_ltb.application.build_context import IssueFactoryContext
from ariadne_ltb.application.issue_compiler import CompiledIssueSpec, compile_issue_specs
from ariadne_ltb.knowledge.compile_graph import (
    compile_deterministic_from_themes,
    compile_from_knowledge_with_provenance,
)
from ariadne_ltb.knowledge.ingest_graph import ingest_sources
from ariadne_ltb.knowledge.llm_adapter import KnowledgeNodeError, default_knowledge_llm, has_deepseek_key
from ariadne_ltb.knowledge.purpose import load_or_derive_project_purpose
from ariadne_ltb.knowledge.reflect import reflect_on_run
from ariadne_ltb.knowledge.store import ProjectKnowledgeStore
from ariadne_ltb.llm import LLMClientError
from ariadne_ltb.storage import AriadneStore


@dataclass(frozen=True)
class IssueCompileProvenance:
    compiler_mode: str
    graph_status: str
    runtime_mode: str
    fallback_reason: str | None = None
    source_insight_ids: list[str] = field(default_factory=list)
    synthesis_theme_ids: list[str] = field(default_factory=list)
    quality_issues: list[str] = field(default_factory=list)
    node_provenance: list[dict[str, object]] = field(default_factory=list)

    def model_dump(self) -> dict[str, object]:
        return {
            "compiler_mode": self.compiler_mode,
            "graph_status": self.graph_status,
            "runtime_mode": self.runtime_mode,
            "fallback_reason": self.fallback_reason,
            "source_insight_ids": self.source_insight_ids,
            "synthesis_theme_ids": self.synthesis_theme_ids,
            "quality_issues": self.quality_issues,
            "node_provenance": self.node_provenance,
        }


@dataclass(frozen=True)
class IssueCompileResult:
    specs: list[CompiledIssueSpec]
    provenance: IssueCompileProvenance


def compile_issues(
    store: AriadneStore,
    *,
    project_id: str,
    title: str,
    north_star: str,
    context: IssueFactoryContext,
) -> list[CompiledIssueSpec]:
    return compile_issues_with_provenance(
        store,
        project_id=project_id,
        title=title,
        north_star=north_star,
        context=context,
    ).specs


def compile_issues_with_provenance(
    store: AriadneStore,
    *,
    project_id: str,
    title: str,
    north_star: str,
    context: IssueFactoryContext,
) -> IssueCompileResult:
    if not has_deepseek_key():
        specs = compile_issue_specs(store, title=title, north_star=north_star, context=context)
        return IssueCompileResult(
            specs=specs,
            provenance=_provenance(
                store,
                project_id,
                compiler_mode="artifact_driven_deterministic_fallback",
                graph_status="skipped",
                runtime_mode="deterministic",
                fallback_reason="missing_deepseek_key",
            ),
        )

    purpose = load_or_derive_project_purpose(
        store,
        project_id=project_id,
        title=title,
        north_star=north_star,
    )
    llm = default_knowledge_llm()
    fallback_reason: str | None = None
    compiler_mode = "project_knowledge_graph"
    graph_status = "completed"
    node_provenance: list[dict[str, object]] = []
    quality_issues: list[str] = []
    try:
        ingest_result = ingest_sources(store, project_id=project_id, purpose=purpose, context=context, llm=llm)
        node_provenance.extend(_node_provenance_from_state(ingest_result))
        graph_result = compile_from_knowledge_with_provenance(
            store,
            project_id=project_id,
            target_project_id=context.manifest.target_project_id,
            purpose=purpose,
            llm=llm,
        )
        specs = graph_result.specs
        node_provenance.extend(graph_result.node_provenance)
        quality_issues = graph_result.quality_issues
    except KnowledgeNodeError as exc:
        fallback_reason = f"{type(exc).__name__}:{exc}"
        node_provenance.append(exc.node_provenance)
        compiler_mode = "deterministic_theme_fallback"
        graph_status = "fallback"
        specs = compile_deterministic_from_themes(store, project_id=project_id)
    except (LLMClientError, ValueError, KeyError, TypeError) as exc:
        fallback_reason = f"{type(exc).__name__}:{exc}"
        compiler_mode = "deterministic_theme_fallback"
        graph_status = "fallback"
        specs = compile_deterministic_from_themes(store, project_id=project_id)
    if not specs:
        if fallback_reason is None:
            fallback_reason = "project_knowledge_returned_no_specs"
        compiler_mode = "deterministic_theme_fallback"
        graph_status = "fallback"
        specs = compile_deterministic_from_themes(store, project_id=project_id)
    if not specs:
        specs = compile_issue_specs(store, title=title, north_star=north_star, context=context)
        compiler_mode = "artifact_driven_deterministic_fallback"
        graph_status = "fallback"
        fallback_reason = fallback_reason or "no_project_knowledge_or_theme_specs"
    return IssueCompileResult(
        specs=specs,
        provenance=_provenance(
            store,
            project_id,
            compiler_mode=compiler_mode,
            graph_status=graph_status,
            runtime_mode="deepseek",
            fallback_reason=fallback_reason,
            quality_issues=quality_issues,
            node_provenance=node_provenance,
        ),
    )


def _provenance(
    store: AriadneStore,
    project_id: str,
    *,
    compiler_mode: str,
    graph_status: str,
    runtime_mode: str,
    fallback_reason: str | None,
    quality_issues: list[str] | None = None,
    node_provenance: list[dict[str, object]] | None = None,
) -> IssueCompileProvenance:
    knowledge_root = store.base / "knowledge" / project_id
    if not knowledge_root.exists():
        return IssueCompileProvenance(
            compiler_mode=compiler_mode,
            graph_status=graph_status,
            runtime_mode=runtime_mode,
            fallback_reason=fallback_reason,
            quality_issues=quality_issues or [],
            node_provenance=node_provenance or [],
        )
    knowledge = ProjectKnowledgeStore(store, project_id)
    return IssueCompileProvenance(
        compiler_mode=compiler_mode,
        graph_status=graph_status,
        runtime_mode=runtime_mode,
        fallback_reason=fallback_reason,
        source_insight_ids=[item.id for item in knowledge.list_source_insights()],
        synthesis_theme_ids=[item.id for item in knowledge.list_synthesis_themes()],
        quality_issues=quality_issues or [],
        node_provenance=node_provenance or [],
    )


def _node_provenance_from_state(state: dict[str, object]) -> list[dict[str, object]]:
    return [dict(item) for item in state.get("node_provenance", []) if isinstance(item, dict)]

__all__ = [
    "IssueCompileProvenance",
    "IssueCompileResult",
    "compile_issues",
    "compile_issues_with_provenance",
    "reflect_on_run",
    "ingest_sources",
]
