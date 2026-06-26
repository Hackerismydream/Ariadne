from __future__ import annotations

from typing import Any

from ariadne_ltb.knowledge.llm_adapter import KnowledgeLLM, call_node_json, node_event
from ariadne_ltb.knowledge.models import ClaimWithEvidence, ProjectPurpose, SourceInsight
from ariadne_ltb.knowledge.prompts import analyze_source_prompt
from ariadne_ltb.models import stable_id


def analyze_source(state: dict[str, Any], llm: KnowledgeLLM) -> dict[str, Any]:
    changed_ids = state.get("changed_source_ids") or []
    index = int(state.get("current_source_index") or 0)
    if index >= len(changed_ids):
        return {}
    source_id = changed_ids[index]
    purpose = ProjectPurpose.model_validate(state["project_purpose"])
    source = dict(state.get("source_documents", {}).get(source_id) or {})
    source["artifacts"] = state.get("source_artifacts", {}).get(source_id, [])
    source["evidence"] = state.get("source_evidence", {}).get(source_id, [])
    response = call_node_json(
        llm,
        analyze_source_prompt(purpose, source),
        "SourceInsightDraft",
        node_name="analyze_source",
    )
    claims = [
        ClaimWithEvidence(
            claim=str(item.get("claim") or ""),
            locator=str(item.get("locator") or source.get("path_or_url") or source_id),
            confidence=float(item.get("confidence", 0.6)),
            source_document_id=source_id,
        )
        for item in response.get("key_claims", [])
        if isinstance(item, dict)
    ]
    existing = (state.get("existing_insights") or {}).get(source_id)
    revision = int(getattr(existing, "revision", 0) or 0) + 1
    insight = SourceInsight(
        id=stable_id("source_insight", state["project_id"], source_id),
        project_id=state["project_id"],
        source_document_id=source_id,
        source_content_hash=str(source.get("content_hash") or ""),
        summary=str(response.get("summary") or source.get("summary") or ""),
        key_claims=claims,
        reusable_patterns=[str(item) for item in response.get("reusable_patterns", [])],
        risks=[str(item) for item in response.get("risks", [])],
        revision=revision,
        last_ingest_cycle=state["cycle_id"],
    )
    return {
        "new_insights": [insight],
        "current_source_index": index + 1,
        "node_provenance": [
            node_event(
                "analyze_source",
                status="completed",
                schema_name="SourceInsightDraft",
                source_document_id=source_id,
                claim_count=len(claims),
            )
        ],
    }
