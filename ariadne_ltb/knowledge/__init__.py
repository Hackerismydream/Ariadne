from __future__ import annotations

from ariadne_ltb.application.build_context import IssueFactoryContext
from ariadne_ltb.application.issue_compiler import CompiledIssueSpec, compile_issue_specs
from ariadne_ltb.knowledge.compile_graph import compile_deterministic_from_themes, compile_from_knowledge
from ariadne_ltb.knowledge.ingest_graph import ingest_sources
from ariadne_ltb.knowledge.llm_adapter import default_knowledge_llm, has_deepseek_key
from ariadne_ltb.knowledge.purpose import load_or_derive_project_purpose
from ariadne_ltb.knowledge.reflect import reflect_on_run
from ariadne_ltb.llm import LLMClientError
from ariadne_ltb.storage import AriadneStore


def compile_issues(
    store: AriadneStore,
    *,
    project_id: str,
    title: str,
    north_star: str,
    context: IssueFactoryContext,
) -> list[CompiledIssueSpec]:
    if not has_deepseek_key():
        return compile_issue_specs(store, title=title, north_star=north_star, context=context)

    purpose = load_or_derive_project_purpose(
        store,
        project_id=project_id,
        title=title,
        north_star=north_star,
    )
    llm = default_knowledge_llm()
    try:
        ingest_sources(store, project_id=project_id, purpose=purpose, context=context, llm=llm)
        specs = compile_from_knowledge(
            store,
            project_id=project_id,
            target_project_id=context.manifest.target_project_id,
            purpose=purpose,
            llm=llm,
        )
    except (LLMClientError, ValueError, KeyError, TypeError):
        specs = compile_deterministic_from_themes(store, project_id=project_id)
    if not specs:
        specs = compile_deterministic_from_themes(store, project_id=project_id)
    if not specs:
        return compile_issue_specs(store, title=title, north_star=north_star, context=context)
    return specs

__all__ = ["compile_issues", "reflect_on_run", "ingest_sources"]
