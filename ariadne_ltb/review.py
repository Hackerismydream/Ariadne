from __future__ import annotations

from ariadne_ltb.models import (
    BuildPacket,
    BuildTicket,
    ExecutionResult,
    ReviewReport,
    ReviewVerdict,
    FailureReason,
    stable_id,
)
from ariadne_ltb.storage import AriadneStore


def review_execution(
    store: AriadneStore,
    ticket: BuildTicket,
    packet: BuildPacket,
    execution: ExecutionResult | None,
) -> ReviewReport:
    passed: list[str] = []
    failed: list[str] = []
    warnings: list[str] = []
    fixes: list[str] = []
    failure_reasons: list[FailureReason] = []

    if packet.evidence:
        passed.append("Build Packet evidence exists")
    else:
        failed.append("Build Packet evidence exists")
        fixes.append("Add evidence to Build Packet.")

    if packet.acceptance_criteria:
        passed.append("Acceptance criteria exist")
    else:
        failed.append("Acceptance criteria exist")
        fixes.append("Add acceptance criteria.")

    if packet.project_relevance:
        passed.append("Project relevance exists")
    else:
        failed.append("Project relevance exists")

    if execution is None:
        failed.append("Execution result exists")
        fixes.append("Run an execution backend.")
    else:
        if execution.blocked:
            failed.append("Execution backend was not blocked")
            fixes.append(execution.block_reason or "Resolve backend block reason.")
            failure_reasons.append(execution.failure_reason or FailureReason.AGENT_ERROR)
        elif execution.exit_code == 0:
            passed.append("Execution exit code is 0")
        else:
            failed.append("Execution exit code is 0")
            fixes.append("Fix execution backend failure.")
            failure_reasons.append(execution.failure_reason or FailureReason.AGENT_ERROR)
        if execution.test_exit_code == 0:
            passed.append("Target project tests passed")
        else:
            failed.append("Target project tests passed")
            fixes.append("Fix failing target project tests.")
            failure_reasons.append(FailureReason.TEST_FAILED)
        if execution.changed_files:
            passed.append("Changed files captured")
        else:
            failed.append("Changed files captured")
        allowed = set(packet.affected_modules)
        changed = set(execution.changed_files)
        if changed and changed.issubset(allowed):
            passed.append("Changed files are within allowed scope")
        else:
            failed.append("Changed files are within allowed scope")
            fixes.append("Restrict execution changes to allowed target paths.")
            failure_reasons.append(FailureReason.SCOPE_VIOLATION)
        if execution.git_diff:
            passed.append("Git diff captured")
        else:
            warnings.append("Git diff is empty or unavailable.")

    non_terminal = [
        run_id for run_id in ticket.agent_run_ids if not store.load_run(run_id).is_terminal
    ]
    if non_terminal:
        failed.append("All Agent Runs have terminal status")
        fixes.append(f"Finish non-terminal runs: {', '.join(non_terminal)}")
    else:
        passed.append("All Agent Runs have terminal status")

    if execution and execution.blocked:
        verdict = ReviewVerdict.BLOCKED
    else:
        verdict = ReviewVerdict.PASS if not failed else ReviewVerdict.NEEDS_FIX
    return ReviewReport(
        id=stable_id("review", ticket.id, execution.id if execution else "missing"),
        ticket_id=ticket.id,
        verdict=verdict,
        passed_checks=passed,
        failed_checks=failed,
        warnings=warnings,
        required_fixes=fixes,
        failure_reasons=list(dict.fromkeys(failure_reasons)),
    )
