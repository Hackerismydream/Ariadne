from __future__ import annotations

from typing import Any

from ariadne_ltb.knowledge.llm_adapter import KnowledgeLLM, call_node_json, node_event
from ariadne_ltb.knowledge.models import (
    ClaimWithEvidence,
    ContradictionRecord,
    ProjectPurpose,
    SourceInsight,
    SynthesisTheme,
)
from ariadne_ltb.knowledge.prompts import detect_contradictions_prompt
from ariadne_ltb.models import stable_id


def detect_contradictions(state: dict[str, Any], llm: KnowledgeLLM) -> dict[str, Any]:
    purpose = ProjectPurpose.model_validate(state["project_purpose"])
    insights = [SourceInsight.model_validate(item) for item in state.get("new_insights", [])]
    themes = [SynthesisTheme.model_validate(item) for item in state.get("updated_themes", [])]
    if not insights:
        return {
            "new_contradictions": [],
            "node_provenance": [
                node_event(
                    "detect_contradictions",
                    status="skipped",
                    schema_name="ContradictionDrafts",
                    reason="no_new_insights",
                )
            ],
        }
    response = call_node_json(
        llm,
        detect_contradictions_prompt(purpose, insights, themes),
        "ContradictionDrafts",
        node_name="detect_contradictions",
    )
    contradictions: list[ContradictionRecord] = []
    for item in response.get("contradictions", []):
        if not isinstance(item, dict):
            continue
        summary = str(item.get("summary") or "").strip()
        if not summary:
            continue
        claims = [
            ClaimWithEvidence.model_validate(claim)
            for claim in item.get("competing_claims", [])
            if isinstance(claim, dict)
        ]
        contradictions.append(
            ContradictionRecord(
                id=stable_id("contradiction", state["project_id"], summary),
                project_id=state["project_id"],
                summary=summary,
                competing_claims=claims,
                status="open",
                resolution=None,
                affected_theme_ids=[str(value) for value in item.get("affected_theme_ids", [])],
            )
        )
    return {
        "new_contradictions": contradictions,
        "node_provenance": [
            node_event(
                "detect_contradictions",
                status="completed",
                schema_name="ContradictionDrafts",
                contradiction_count=len(contradictions),
            )
        ],
    }
