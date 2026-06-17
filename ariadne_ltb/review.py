from __future__ import annotations

import json
import os
from typing import Any

from pydantic import Field, ValidationError

from ariadne_ltb.llm import DeepSeekClient, LLMClientError, load_local_env, redact_secrets
from ariadne_ltb.models import (
    AriadneModel,
    BuildPacket,
    BuildTicket,
    ExecutionResult,
    FailureReason,
    ReviewReport,
    ReviewVerdict,
    stable_id,
)
from ariadne_ltb.storage import AriadneStore


class LLMReviewPayload(AriadneModel):
    verdict: ReviewVerdict
    passed_checks: list[str] = Field(default_factory=list)
    failed_checks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    required_fixes: list[str] = Field(default_factory=list)
    failure_reasons: list[FailureReason] = Field(default_factory=list)


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
    injection_findings = packet.metadata.get("prompt_injection_findings", [])
    if packet.metadata.get("trust_boundary") == "untrusted_external_context":
        passed.append("Source trust boundary recorded")
    else:
        warnings.append("Source trust boundary metadata is missing.")
    if injection_findings:
        warnings.append(
            f"Prompt-injection patterns detected in untrusted source: {len(injection_findings)} finding(s)."
        )

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


def review_execution_with_llm(
    store: AriadneStore,
    ticket: BuildTicket,
    packet: BuildPacket,
    execution: ExecutionResult | None,
    client: DeepSeekClient | None = None,
) -> ReviewReport:
    load_local_env(store.root)
    baseline = review_execution(store, ticket, packet, execution)
    if not os.environ.get("DEEPSEEK_API_KEY") and client is None:
        return _blocked_llm_review(
            ticket,
            execution,
            baseline,
            "DEEPSEEK_API_KEY is required for --reviewer llm.",
        )

    llm_client = client or DeepSeekClient()
    try:
        data = llm_client.complete_json(_llm_review_prompt(ticket, packet, execution, baseline), "ariadne_review_report")
        payload = LLMReviewPayload.model_validate(data)
    except (LLMClientError, ValidationError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return _blocked_llm_review(ticket, execution, baseline, redact_secrets(f"LLM reviewer failed: {exc}"))

    verdict = _conservative_verdict(baseline.verdict, payload.verdict, payload.failed_checks)
    return ReviewReport(
        id=stable_id("review", ticket.id, execution.id if execution else "missing", "llm"),
        ticket_id=ticket.id,
        verdict=verdict,
        passed_checks=_dedupe([*baseline.passed_checks, *payload.passed_checks]),
        failed_checks=_dedupe([*baseline.failed_checks, *payload.failed_checks]),
        warnings=_dedupe([*baseline.warnings, *payload.warnings, "Reviewer mode: llm"]),
        required_fixes=_dedupe([*baseline.required_fixes, *payload.required_fixes]),
        failure_reasons=list(dict.fromkeys([*baseline.failure_reasons, *payload.failure_reasons])),
    )


def _blocked_llm_review(
    ticket: BuildTicket,
    execution: ExecutionResult | None,
    baseline: ReviewReport,
    reason: str,
) -> ReviewReport:
    return ReviewReport(
        id=stable_id("review", ticket.id, execution.id if execution else "missing", "llm-blocked"),
        ticket_id=ticket.id,
        verdict=ReviewVerdict.BLOCKED,
        passed_checks=baseline.passed_checks,
        failed_checks=_dedupe([*baseline.failed_checks, "LLM reviewer completed"]),
        warnings=_dedupe([*baseline.warnings, "Reviewer mode: llm"]),
        required_fixes=_dedupe([*baseline.required_fixes, reason]),
        failure_reasons=list(dict.fromkeys([*baseline.failure_reasons, FailureReason.COMMAND_UNAVAILABLE])),
    )


def _conservative_verdict(
    baseline: ReviewVerdict,
    llm_verdict: ReviewVerdict,
    llm_failed_checks: list[str],
) -> ReviewVerdict:
    if baseline is ReviewVerdict.BLOCKED or llm_verdict is ReviewVerdict.BLOCKED:
        return ReviewVerdict.BLOCKED
    if baseline is ReviewVerdict.NEEDS_HUMAN_REVIEW or llm_verdict is ReviewVerdict.NEEDS_HUMAN_REVIEW:
        return ReviewVerdict.NEEDS_HUMAN_REVIEW
    if baseline is ReviewVerdict.NEEDS_FIX or llm_verdict is ReviewVerdict.NEEDS_FIX or llm_failed_checks:
        return ReviewVerdict.NEEDS_FIX
    return ReviewVerdict.PASS


def _llm_review_prompt(
    ticket: BuildTicket,
    packet: BuildPacket,
    execution: ExecutionResult | None,
    baseline: ReviewReport,
) -> str:
    execution_summary: dict[str, Any] = (
        {
            "backend": execution.backend_name,
            "blocked": execution.blocked,
            "block_reason": execution.block_reason,
            "exit_code": execution.exit_code,
            "test_exit_code": execution.test_exit_code,
            "changed_files": execution.changed_files,
            "warnings": execution.warnings,
            "stderr_tail": execution.stderr[-2000:],
            "test_stderr_tail": execution.test_stderr[-2000:],
            "git_diff_tail": execution.git_diff[-4000:],
        }
        if execution
        else {"missing": True}
    )
    payload = {
        "instruction": "Return json only. Be conservative and identify product risks.",
        "expected_json_shape": {
            "verdict": "pass|needs_fix|blocked|needs_human_review",
            "passed_checks": [],
            "failed_checks": [],
            "warnings": [],
            "required_fixes": [],
            "failure_reasons": [],
        },
        "ticket": {"key": ticket.key, "title": ticket.title, "status": ticket.status.value},
        "build_packet": {
            "decision": packet.build_decision.value,
            "tasks": packet.tasks,
            "acceptance_criteria": packet.acceptance_criteria,
            "affected_modules": packet.affected_modules,
            "risks": packet.risks,
            "assumptions": packet.assumptions,
        },
        "execution": execution_summary,
        "deterministic_review": baseline.model_dump(mode="json"),
    }
    return json.dumps(payload, indent=2)


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))
