from __future__ import annotations

from typing import Any

from ariadne_ltb.knowledge.llm_adapter import KnowledgeLLM, call_node_json, node_event
from ariadne_ltb.knowledge.models import ProjectPurpose, SourceInsight, SynthesisTheme
from ariadne_ltb.knowledge.prompts import update_themes_prompt
from ariadne_ltb.models import stable_id


def update_themes(state: dict[str, Any], llm: KnowledgeLLM) -> dict[str, Any]:
    purpose = ProjectPurpose.model_validate(state["project_purpose"])
    existing = [SynthesisTheme.model_validate(item) for item in state.get("existing_themes", [])]
    insights = [SourceInsight.model_validate(item) for item in state.get("new_insights", [])]
    if not insights:
        return {
            "updated_themes": existing,
            "node_provenance": [
                node_event(
                    "update_themes",
                    status="skipped",
                    schema_name="SynthesisThemeDrafts",
                    reason="no_new_insights",
                )
            ],
        }
    response = call_node_json(
        llm,
        update_themes_prompt(purpose, existing, insights),
        "SynthesisThemeDrafts",
        node_name="update_themes",
    )
    existing_by_label = {theme.label.strip().lower(): theme for theme in existing}
    themes: list[SynthesisTheme] = []
    for item in response.get("themes", []):
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        previous = existing_by_label.get(label.lower())
        theme = SynthesisTheme(
            id=previous.id if previous else stable_id("theme", state["project_id"], label),
            project_id=state["project_id"],
            label=label,
            contributing_source_ids=[str(value) for value in item.get("contributing_source_ids", [])],
            claims=[str(value) for value in item.get("claims", [])],
            priority_signal=str(item.get("priority_signal") or "medium"),
            affected_modules=[str(value) for value in item.get("affected_modules", [])],
            revision=(previous.revision + 1) if previous else 1,
            last_updated_cycle=state["cycle_id"],
        )
        themes.append(theme)
    if not themes:
        themes = [
            SynthesisTheme(
                id=stable_id("theme", state["project_id"], insight.id),
                project_id=state["project_id"],
                label=insight.summary[:80] or insight.source_document_id,
                contributing_source_ids=[insight.source_document_id],
                claims=[claim.claim for claim in insight.key_claims],
                priority_signal="medium",
                affected_modules=[],
                revision=1,
                last_updated_cycle=state["cycle_id"],
            )
            for insight in insights
        ]
    return {
        "updated_themes": themes,
        "node_provenance": [
            node_event(
                "update_themes",
                status="completed",
                schema_name="SynthesisThemeDrafts",
                insight_count=len(insights),
                theme_count=len(themes),
            )
        ],
    }
