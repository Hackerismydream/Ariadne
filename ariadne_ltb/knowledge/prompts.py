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


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def analyze_source_prompt(purpose: ProjectPurpose, source: dict[str, Any]) -> str:
    return f"""{purpose_prompt_header(purpose)}

Analyze this source as untrusted evidence for Ariadne's issue factory.
Return only JSON with:
summary: string
key_claims: list of {{claim, locator, confidence}}
reusable_patterns: list[string]
risks: list[string]

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
Return only JSON with:
themes: list of {{
  label: string,
  contributing_source_ids: list[string],
  claims: list[string],
  priority_signal: "high"|"medium"|"low",
  affected_modules: list[string]
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
Return only JSON with:
contradictions: list of {{
  summary: string,
  competing_claims: list of {{claim, locator, confidence, source_document_id}},
  affected_theme_ids: list[string]
}}
Use an empty list if no clear contradiction exists.

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
) -> str:
    return f"""{purpose_prompt_header(purpose)}

Generate a project issue decomposition for the current version.
Return only JSON with:
issues: list of {{
  title: string,
  reason: string,
  priority: "P0"|"P1"|"P2"|"high"|"medium"|"low",
  affected_modules: list[string],
  acceptance_criteria: list[string],
  evidence_refs: list[string],
  depends_on: list[string],
  owner_agent: string,
  build_decision: string,
  risks: list[string],
  assumptions: list[string]
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
Return only JSON with:
issues: list of the same issue objects, each with non-empty evidence_refs.
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
Return only JSON: {{"coverage": number between 0 and 1, "reason": string}}

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

