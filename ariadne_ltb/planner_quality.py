from __future__ import annotations

from ariadne_ltb.models import BuildPacket


def score_build_packet(packet: BuildPacket) -> dict[str, float]:
    evidence_coverage_score = min(len(packet.evidence) / 5, 1.0)
    task_clarity_score = 1.0 if packet.tasks and all(len(task) >= 12 for task in packet.tasks) else 0.4
    acceptance_criteria_score = min(len(packet.acceptance_criteria) / 3, 1.0)
    scope_risk_score = 1.0 if packet.affected_modules and len(packet.affected_modules) <= 6 else 0.5
    overall_quality = round(
        (
            evidence_coverage_score
            + task_clarity_score
            + acceptance_criteria_score
            + scope_risk_score
        )
        / 4,
        3,
    )
    return {
        "evidence_coverage_score": round(evidence_coverage_score, 3),
        "task_clarity_score": round(task_clarity_score, 3),
        "acceptance_criteria_score": round(acceptance_criteria_score, 3),
        "scope_risk_score": round(scope_risk_score, 3),
        "overall_quality": overall_quality,
    }
