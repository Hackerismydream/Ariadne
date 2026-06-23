from __future__ import annotations

from typing import Any

from ariadne_ltb.knowledge.llm_adapter import KnowledgeLLM
from ariadne_ltb.knowledge.models import BlockerLearning, ContradictionRecord, ProjectPurpose
from ariadne_ltb.knowledge.prompts import goal_coverage_prompt


def quality_gate(state: dict[str, Any], llm: KnowledgeLLM) -> dict[str, Any]:
    specs = [dict(item) for item in state.get("validated_issues", [])]
    issues: list[str] = list(state.get("quality_issues", []))
    score = 1.0

    if not (3 <= len(specs) <= 20):
        issues.append("count_out_of_range")
    titles = [str(item.get("title") or "").strip().lower() for item in specs]
    if len(set(titles)) < len(titles):
        issues.append("duplicate_titles")
    for spec in specs:
        title = str(spec.get("title") or "")[:30]
        if len(spec.get("acceptance_criteria", [])) < 2:
            issues.append(f"weak_criteria:{title}")
        if not spec.get("affected_modules"):
            issues.append(f"no_modules:{title}")

    purpose = ProjectPurpose.model_validate(state["project_purpose"])
    priority_specs = [
        spec
        for spec in specs
        if str(spec.get("priority") or "").lower() in {"p0", "high"}
    ]
    if priority_specs and purpose.success_signals:
        try:
            coverage_response = llm.complete_json(
                goal_coverage_prompt(purpose, priority_specs),
                "GoalCoverageScore",
            )
            coverage = float(coverage_response.get("coverage", 0.0))
        except Exception:
            coverage = 0.0
        if coverage < 0.6:
            issues.append(f"low_goal_coverage:{coverage:.2f}")
            score -= 0.3

    blockers = [BlockerLearning.model_validate(item) for item in state.get("unresolved_blockers", [])]
    for blocker in blockers:
        referenced = any(
            blocker.blocker_reason
            in (
                str(spec.get("reason") or "")
                + " "
                + " ".join(str(item) for item in spec.get("acceptance_criteria", []))
            ).lower()
            for spec in specs
        )
        if not referenced:
            issues.append(f"unresolved_blocker_ignored:{blocker.blocker_reason}")

    contradictions = [
        ContradictionRecord.model_validate(item) for item in state.get("unresolved_contradictions", [])
    ]
    for contradiction in contradictions:
        referenced = any(contradiction.id in spec.get("evidence_refs", []) for spec in specs)
        if not referenced and contradiction.status == "open":
            issues.append(f"unresolved_contradiction:{contradiction.id}")

    score = max(0.0, score - len(issues) * 0.1)
    return {
        "quality_score": score,
        "quality_issues": issues,
        "compiled_specs": specs if score >= 0.6 and not _has_hard_failure(issues) else [],
        "used_fallback": False,
    }


def _has_hard_failure(issues: list[str]) -> bool:
    return "dependency_cycle" in issues or "count_out_of_range" in issues

