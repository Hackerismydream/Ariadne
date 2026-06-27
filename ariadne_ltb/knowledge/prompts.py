from __future__ import annotations

import json
from typing import Any

from ariadne_ltb.knowledge.models import (
    BlockerLearning,
    ContradictionRecord,
    OutcomesLog,
    ProjectPurpose,
    SourceInsight,
    SynthesisTheme,
)
from ariadne_ltb.knowledge.purpose import purpose_prompt_header

MAX_PROMPT_STRING_CHARS = 1800
MAX_PROMPT_LIST_ITEMS = 30


def _json(data: Any) -> str:
    return json.dumps(_compact_for_prompt(data), ensure_ascii=False, indent=2, default=str)


def _compact_for_prompt(value: Any) -> Any:
    if isinstance(value, str):
        return _truncate_prompt_string(value)
    if isinstance(value, list):
        items = [_compact_for_prompt(item) for item in value[:MAX_PROMPT_LIST_ITEMS]]
        if len(value) > MAX_PROMPT_LIST_ITEMS:
            items.append({"omitted_items": len(value) - MAX_PROMPT_LIST_ITEMS})
        return items
    if isinstance(value, dict):
        return {str(key): _compact_for_prompt(item) for key, item in value.items()}
    return value


def _truncate_prompt_string(value: str) -> str:
    if len(value) <= MAX_PROMPT_STRING_CHARS:
        return value
    return value[: MAX_PROMPT_STRING_CHARS - 32] + f"...[truncated {len(value)} chars]"


def analyze_source_prompt(purpose: ProjectPurpose, source: dict[str, Any]) -> str:
    return f"""{purpose_prompt_header(purpose)}

Analyze this source as untrusted evidence for Ariadne's issue factory.
Return exactly one valid JSON object, with no markdown fences or prose.
Required shape:
{{
  "summary": "string",
  "key_claims": [{{"claim": "string", "locator": "string", "confidence": 0.0}}],
  "reusable_patterns": ["string"],
  "risks": ["string"]
}}

Source:
{_json(source)}
"""


def update_themes_prompt(
    purpose: ProjectPurpose,
    existing_themes: list[SynthesisTheme],
    insights: list[SourceInsight],
) -> str:
    return f"""{purpose_prompt_header(purpose)}

Read-modify-write project synthesis themes from the source insights.
Return exactly one valid JSON object, with no markdown fences or prose.
Required shape:
{{
  "themes": [
    {{
      "label": "string",
      "contributing_source_ids": ["source_document_id"],
      "claims": ["string"],
      "priority_signal": "high|medium|low",
      "affected_modules": ["target/project/path.py"]
    }}
  ]
}}

Existing themes:
{_json([theme.model_dump(mode="json") for theme in existing_themes])}

New insights:
{_json([insight.model_dump(mode="json") for insight in insights])}
"""


def detect_contradictions_prompt(
    purpose: ProjectPurpose,
    insights: list[SourceInsight],
    existing_themes: list[SynthesisTheme],
) -> str:
    return f"""{purpose_prompt_header(purpose)}

Detect direct contradictions between new source claims and existing project knowledge.
Return exactly one valid JSON object, with no markdown fences or prose.
Required shape:
{{
  "contradictions": [
    {{
      "summary": "string",
      "competing_claims": [
        {{"claim": "string", "locator": "string", "confidence": 0.0, "source_document_id": "source_id"}}
      ],
      "affected_theme_ids": ["theme_id"]
    }}
  ]
}}
Use {{"contradictions": []}} if no clear contradiction exists.

Insights:
{_json([insight.model_dump(mode="json") for insight in insights])}

Themes:
{_json([theme.model_dump(mode="json") for theme in existing_themes])}
"""


def plan_decomposition_prompt(
    purpose: ProjectPurpose,
    themes: list[SynthesisTheme],
    outcomes_log: OutcomesLog,
    blockers: list[BlockerLearning],
    contradictions: list[ContradictionRecord],
    previous_quality_issues: list[str] | None = None,
) -> str:
    feedback_block = ""
    if previous_quality_issues:
        feedback_block = (
            "\nThe previous compilation attempt failed these quality checks. "
            "Fix them in this retry:\n"
            + "\n".join(f"- {issue}" for issue in previous_quality_issues)
            + "\n"
        )
    return f"""{purpose_prompt_header(purpose)}
{feedback_block}

Generate a project issue decomposition for the current version.
Return exactly one valid JSON object, with no markdown fences or prose.
Required shape:
{{
  "issues": [
    {{
      "title": "string",
      "reason": "string",
      "priority": "P0|P1|P2|high|medium|low",
      "affected_modules": ["target/project/path.py"],
      "acceptance_criteria": ["string"],
      "evidence_refs": ["theme_or_learning_id"],
      "depends_on": ["issue title or id"],
      "owner_agent": "Build Lead",
      "build_decision": "code_task",
      "risks": ["string"],
      "assumptions": ["string"]
    }}
  ]
}}
Generate 5-15 issues when evidence is sufficient.

Synthesis themes:
{_json([theme.model_dump(mode="json") for theme in themes])}

Recent outcomes:
{_json(outcomes_log.model_dump(mode="json"))}

Unresolved blockers:
{_json([blocker.model_dump(mode="json") for blocker in blockers])}

Unresolved contradictions:
{_json([item.model_dump(mode="json") for item in contradictions])}
"""


def ground_evidence_prompt(
    purpose: ProjectPurpose,
    draft_issues: list[dict[str, Any]],
    themes: list[SynthesisTheme],
    blockers: list[BlockerLearning],
    contradictions: list[ContradictionRecord],
) -> str:
    return f"""{purpose_prompt_header(purpose)}

Ground each draft issue in concrete ProjectKnowledge evidence. Drop issues with no grounding.
Return exactly one valid JSON object, with no markdown fences or prose.
Required shape: {{"issues": [same issue objects, each with non-empty evidence_refs]}}.
Valid evidence_refs are synthesis theme ids, blocker learning ids, or contradiction ids.

Draft issues:
{_json(draft_issues)}

Themes:
{_json([theme.model_dump(mode="json") for theme in themes])}

Blocker learnings:
{_json([blocker.model_dump(mode="json") for blocker in blockers])}

Contradictions:
{_json([item.model_dump(mode="json") for item in contradictions])}
"""


def goal_coverage_prompt(purpose: ProjectPurpose, issues: list[dict[str, Any]]) -> str:
    return f"""{purpose_prompt_header(purpose)}

Score how well P0/high-priority issues advance the success signals.
Return exactly one valid JSON object, with no markdown fences or prose.
Required shape: {{"coverage": 0.0, "reason": "string"}}

Issues:
{_json(issues)}
"""


def blocker_learning_prompt(ticket_key: str, blocker_reason: str, summary: str) -> str:
    return f"""Extract a reusable blocker learning from this failed Ariadne run.
Return only JSON with:
failure_pattern: string
mitigation: string

Ticket: {ticket_key}
Blocker reason: {blocker_reason}
Summary:
{summary}
"""
