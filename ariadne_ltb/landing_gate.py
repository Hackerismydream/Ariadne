from __future__ import annotations

from pathlib import Path

from ariadne_ltb.models import (
    Artifact,
    ArtifactType,
    BuildTicket,
    LandingEvidence,
    LandingGateCheck,
    LandingGateCheckStatus,
    LandingGateReport,
    LandingGateStatus,
    ReviewVerdict,
    stable_id,
)
from ariadne_ltb.storage import AriadneStore


REQUIRED_LINKED_ARTIFACTS = {
    "execution_log",
    "git_diff",
    "changed_files",
    "test_output",
    "review_report",
    "memory_record",
    "next_tickets",
    "feishu_plan",
    "orchestrator_result",
}


def evaluate_landing_gate_for_ticket(store: AriadneStore, ticket: BuildTicket) -> tuple[LandingGateReport, Artifact]:
    evidence_artifact = latest_landing_evidence_json_artifact(store, ticket)
    evidence = _load_landing_evidence(evidence_artifact)
    report = evaluate_landing_gate(ticket, evidence, evidence_artifact.path if evidence_artifact else None)
    artifact = store.write_artifact(
        ticket.id,
        "build_lead",
        ArtifactType.LANDING_GATE_REPORT,
        "landing_gate_report.json",
        report.model_dump_json(indent=2) + "\n",
        f"Landing gate report: {report.status.value}",
        metadata={
            "landing_gate_report_id": report.id,
            "status": report.status.value,
            "landing_evidence_id": report.landing_evidence_id or "",
        },
    )
    ticket = (
        store.load_ticket(ticket.id)
        .with_artifacts([artifact])
        .append_event(
            "landing_gate_evaluated",
            "Build Lead",
            f"Landing gate evaluated: {report.status.value}.",
            payload_ref=artifact.id,
        )
        .model_copy(
            deep=True,
            update={
                "metadata": store.load_ticket(ticket.id).metadata
                | {
                    "landing_gate_report_artifact_id": artifact.id,
                    "landing_gate_report_path": artifact.path,
                    "landing_gate_status": report.status.value,
                }
            },
        )
    )
    store.save_ticket(ticket)
    return report, artifact


def evaluate_landing_gate(
    ticket: BuildTicket,
    evidence: LandingEvidence | None,
    evidence_path: str | None,
) -> LandingGateReport:
    checks: list[LandingGateCheck] = []
    if evidence is None:
        checks.append(
            _check(
                "landing_evidence_present",
                LandingGateCheckStatus.FAIL,
                "Landing evidence JSON artifact is missing or invalid.",
                evidence_path,
            )
        )
        return _report(ticket, None, evidence_path, checks)

    checks.extend(
        [
            _check(
                "landing_evidence_complete",
                LandingGateCheckStatus.PASS
                if not evidence.partial and not evidence.missing_fields
                else LandingGateCheckStatus.FAIL,
                "Landing evidence is complete."
                if not evidence.partial and not evidence.missing_fields
                else "Landing evidence is partial or has missing fields.",
                evidence_path,
            ),
            _check(
                "execution_not_blocked",
                LandingGateCheckStatus.PASS
                if not evidence.gate_inputs.get("execution_blocked")
                else LandingGateCheckStatus.FAIL,
                "Execution was not blocked."
                if not evidence.gate_inputs.get("execution_blocked")
                else str(evidence.gate_inputs.get("block_reason") or "Execution was blocked."),
                evidence.execution_result_id,
            ),
            _check(
                "execution_exit_zero",
                LandingGateCheckStatus.PASS
                if evidence.gate_inputs.get("execution_exit_code") == 0
                else LandingGateCheckStatus.FAIL,
                f"Execution exit code: {evidence.gate_inputs.get('execution_exit_code')}.",
                evidence.execution_result_id,
            ),
            _check(
                "review_passed",
                LandingGateCheckStatus.PASS
                if evidence.review_verdict is ReviewVerdict.PASS
                else LandingGateCheckStatus.FAIL,
                f"Review verdict: {evidence.review_verdict.value}.",
                evidence.review_report_id,
            ),
            _tests_check(evidence),
            _linked_artifacts_check(evidence),
            _changed_files_check(evidence),
        ]
    )
    if evidence.backend_name in {"codex", "claude-code", "shell"}:
        checks.append(
            _check(
                "external_execution_gate_confirmed",
                LandingGateCheckStatus.PASS
                if evidence.gate_inputs.get("external_execution_enabled")
                else LandingGateCheckStatus.FAIL,
                "External execution gate was enabled for the real backend."
                if evidence.gate_inputs.get("external_execution_enabled")
                else "Real backend evidence must come from an externally enabled run.",
                evidence_path,
            )
        )
    return _report(ticket, evidence, evidence_path, checks)


def latest_landing_evidence_json_artifact(store: AriadneStore, ticket: BuildTicket) -> Artifact | None:
    for artifact_id in reversed(ticket.artifact_ids):
        artifact = store.load_artifact(artifact_id)
        if artifact.artifact_type is not ArtifactType.LANDING_EVIDENCE:
            continue
        if artifact.metadata.get("format") == "json" or artifact.path.endswith(".json"):
            return artifact
    return None


def _load_landing_evidence(artifact: Artifact | None) -> LandingEvidence | None:
    if artifact is None:
        return None
    try:
        return LandingEvidence.model_validate_json(Path(artifact.path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _tests_check(evidence: LandingEvidence) -> LandingGateCheck:
    if not evidence.test_results:
        return _check("tests_passed", LandingGateCheckStatus.WARN, "No test result was recorded.", None)
    failed = [test for test in evidence.test_results if test.status not in {"pass", "passed"}]
    if failed:
        return _check(
            "tests_passed",
            LandingGateCheckStatus.FAIL,
            f"{len(failed)} test command(s) did not pass.",
            failed[0].output_artifact_path,
        )
    return _check("tests_passed", LandingGateCheckStatus.PASS, "All recorded test commands passed.", None)


def _linked_artifacts_check(evidence: LandingEvidence) -> LandingGateCheck:
    linked = {artifact.kind for artifact in evidence.linked_artifacts}
    missing = sorted(REQUIRED_LINKED_ARTIFACTS - linked)
    if missing:
        return _check(
            "linked_artifacts_present",
            LandingGateCheckStatus.FAIL,
            f"Missing linked artifacts: {', '.join(missing)}.",
            evidence.orchestrator_result_path,
        )
    return _check(
        "linked_artifacts_present",
        LandingGateCheckStatus.PASS,
        "All required linked artifacts are present.",
        evidence.orchestrator_result_path,
    )


def _changed_files_check(evidence: LandingEvidence) -> LandingGateCheck:
    if evidence.changed_files:
        return _check(
            "changed_files_recorded",
            LandingGateCheckStatus.PASS,
            f"Changed files recorded: {len(evidence.changed_files)}.",
            None,
        )
    return _check(
        "changed_files_recorded",
        LandingGateCheckStatus.WARN,
        "No changed files were recorded; this may be expected for non-code tickets.",
        None,
    )


def _report(
    ticket: BuildTicket,
    evidence: LandingEvidence | None,
    evidence_path: str | None,
    checks: list[LandingGateCheck],
) -> LandingGateReport:
    blockers = [check.summary for check in checks if check.status is LandingGateCheckStatus.FAIL]
    warnings = [check.summary for check in checks if check.status is LandingGateCheckStatus.WARN]
    status = (
        LandingGateStatus.BLOCKED
        if blockers
        else LandingGateStatus.NEEDS_REVIEW
        if warnings
        else LandingGateStatus.READY
    )
    return LandingGateReport(
        id=stable_id("landing_gate", ticket.id, evidence.id if evidence else "missing"),
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        status=status,
        landing_evidence_id=evidence.id if evidence else None,
        landing_evidence_path=evidence_path,
        checks=checks,
        blockers=blockers,
        warnings=warnings,
        recommended_action=_recommended_action(status),
    )


def _recommended_action(status: LandingGateStatus) -> str:
    if status is LandingGateStatus.READY:
        return "ready_for_human_or_confirmed_merge_gate"
    if status is LandingGateStatus.NEEDS_REVIEW:
        return "review_warnings_before_landing"
    return "fix_blockers_before_landing"


def _check(
    name: str,
    status: LandingGateCheckStatus,
    summary: str,
    evidence_ref: str | None,
) -> LandingGateCheck:
    return LandingGateCheck(name=name, status=status, summary=summary, evidence_ref=evidence_ref)
