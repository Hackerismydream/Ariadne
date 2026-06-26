from __future__ import annotations

from typing import Any

from ariadne_ltb.knowledge.llm_adapter import KnowledgeLLM, call_node_json, node_event
from ariadne_ltb.knowledge.models import BlockerLearning, ContradictionRecord, ProjectPurpose, SynthesisTheme
from ariadne_ltb.knowledge.prompts import ground_evidence_prompt


def ground_evidence(state: dict[str, Any], llm: KnowledgeLLM) -> dict[str, Any]:
    purpose = ProjectPurpose.model_validate(state["project_purpose"])
    themes = [SynthesisTheme.model_validate(item) for item in state.get("themes", [])]
    blockers = [BlockerLearning.model_validate(item) for item in state.get("unresolved_blockers", [])]
    contradictions = [
        ContradictionRecord.model_validate(item) for item in state.get("unresolved_contradictions", [])
    ]
    draft = list(state.get("draft_issues", []))
    valid_refs = {theme.id for theme in themes} | {item.id for item in blockers} | {
        item.id for item in contradictions
    }
    fallback_refs = [theme.id for theme in themes[:3]]
    response = call_node_json(
        llm,
        ground_evidence_prompt(purpose, draft, themes, blockers, contradictions),
        "GroundedIssueDrafts",
        node_name="ground_evidence",
    )
    grounded: list[dict[str, Any]] = []
    for item in response.get("issues", []):
        if not isinstance(item, dict):
            continue
        refs = [str(ref) for ref in item.get("evidence_refs", []) if str(ref) in valid_refs]
        if not refs:
            refs = fallback_refs
        if refs:
            grounded.append(item | {"evidence_refs": refs})
    if not grounded and fallback_refs:
        grounded = [dict(item) | {"evidence_refs": fallback_refs} for item in draft if isinstance(item, dict)]
    return {
        "grounded_issues": grounded,
        "node_provenance": [
            node_event(
                "ground_evidence",
                status="completed",
                schema_name="GroundedIssueDrafts",
                draft_issue_count=len(draft),
                grounded_issue_count=len(grounded),
            )
        ],
    }
