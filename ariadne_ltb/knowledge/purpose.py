from __future__ import annotations

from ariadne_ltb.knowledge.models import ProjectPurpose
from ariadne_ltb.knowledge.store import ProjectKnowledgeStore
from ariadne_ltb.models import stable_id
from ariadne_ltb.storage import AriadneStore


def load_or_derive_project_purpose(
    store: AriadneStore,
    *,
    project_id: str,
    title: str,
    north_star: str,
) -> ProjectPurpose:
    knowledge_store = ProjectKnowledgeStore(store, project_id)
    try:
        return knowledge_store.load_project_purpose()
    except FileNotFoundError:
        purpose = ProjectPurpose(
            project_id=project_id,
            title=title or project_id,
            one_line=north_star or title,
            why_this_exists=north_star or title,
            target_users=[],
            success_signals=[north_star] if north_star else [],
            out_of_scope=[],
            constraints=["Local-first Ariadne v1.x ticket-centered workbench."],
        )
        return knowledge_store.save_project_purpose(purpose)


def purpose_prompt_header(purpose: ProjectPurpose) -> str:
    return "\n".join(
        [
            f"You are working on project: {purpose.title}",
            f"Why this project exists: {purpose.why_this_exists}",
            f"Target users: {purpose.target_users}",
            f"Success signals to advance: {purpose.success_signals}",
            f"Out of scope (do NOT propose): {purpose.out_of_scope}",
            f"Engineering constraints: {purpose.constraints}",
        ]
    )


def project_cycle_id(prefix: str, project_id: str, *parts: object) -> str:
    return stable_id(prefix, project_id, *parts)

