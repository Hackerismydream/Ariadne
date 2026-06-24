from __future__ import annotations

from typing import Any

from ariadne_ltb.knowledge.store import ProjectKnowledgeStore


def load_knowledge(state: dict[str, Any]) -> dict[str, Any]:
    knowledge_store = ProjectKnowledgeStore(state["store"], state["project_id"])
    return {
        "project_purpose": knowledge_store.load_project_purpose(),
        "themes": knowledge_store.list_synthesis_themes(),
        "outcomes_log": knowledge_store.load_outcomes_log(),
        "unresolved_blockers": knowledge_store.list_blocker_learnings(),
        "unresolved_contradictions": knowledge_store.list_unresolved_contradictions(),
    }

