from __future__ import annotations

from typing import Any

from ariadne_ltb.knowledge.llm_adapter import KnowledgeLLM
from ariadne_ltb.knowledge.models import (
    BlockerLearning,
    ContradictionRecord,
    OutcomesLog,
    ProjectPurpose,
    SynthesisTheme,
)
from ariadne_ltb.knowledge.prompts import plan_decomposition_prompt
from ariadne_ltb.knowledge.theme_compiler import theme_issue_dicts


def plan_decomposition(state: dict[str, Any], llm: KnowledgeLLM) -> dict[str, Any]:
    purpose = ProjectPurpose.model_validate(state["project_purpose"])
    themes = [SynthesisTheme.model_validate(item) for item in state.get("themes", [])][:15]
    outcomes = OutcomesLog.model_validate(state.get("outcomes_log") or {"project_id": state["project_id"]})
    blockers = [BlockerLearning.model_validate(item) for item in state.get("unresolved_blockers", [])]
    contradictions = [
        ContradictionRecord.model_validate(item) for item in state.get("unresolved_contradictions", [])
    ]
    try:
        response = llm.complete_json(
            plan_decomposition_prompt(purpose, themes, outcomes, blockers, contradictions),
            "IssueDecompositionDrafts",
        )
    except Exception:
        return {
            "draft_issues": _drafts_from_themes(themes),
            "compile_attempts": int(state.get("compile_attempts") or 0) + 1,
            "quality_issues": [*state.get("quality_issues", []), "llm_plan_decomposition_failed"],
        }
    issues = [item for item in response.get("issues", []) if isinstance(item, dict)]
    return {"draft_issues": issues, "compile_attempts": int(state.get("compile_attempts") or 0) + 1}


def _drafts_from_themes(themes: list[SynthesisTheme]) -> list[dict[str, Any]]:
    return theme_issue_dicts(themes)
