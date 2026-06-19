from __future__ import annotations

from pathlib import Path
from typing import Any

from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.llm import DeepSeekClient
from ariadne_ltb.models import ExecutionResult, FailureReason, ReviewVerdict
from ariadne_ltb.review import review_execution, review_execution_with_llm
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


class _ReviewTransport:
    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        timeout_seconds: int,
    ) -> dict[str, Any]:
        return {
            "model": "deepseek-v4-pro",
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"id":"extra_review_id","ticket_id":"extra_ticket",'
                            '"verdict":"pass","reviewer_mode":"deterministic",'
                            '"risk_score":0.1,"passed_checks":["LLM reviewer completed"],'
                            '"failed_checks":[],"warnings":[],"required_fixes":[],'
                            '"failure_reasons":[],"created_at":"2026-06-19T18:25:22Z"}'
                        )
                    }
                }
            ],
            "usage": {"total_tokens": 12},
        }


def test_deterministic_review_records_acceptance_evidence_and_low_risk(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    packet = store.load_build_packet(ticket.build_packet_id)
    execution = ExecutionResult(
        id="execution_review_pass",
        ticket_id=ticket.id,
        backend_name="codex",
        dry_run=False,
        command="codex exec",
        exit_code=0,
        stdout="done",
        test_exit_code=0,
        test_stdout="passed",
        changed_files=["demo_todo/cli.py", "tests/test_cli.py"],
        git_diff="diff --git a/demo_todo/cli.py b/demo_todo/cli.py",
    )

    review = review_execution(store, ticket, packet, execution)

    assert review.verdict is ReviewVerdict.PASS
    assert review.reviewer_mode == "deterministic"
    assert 0 <= review.risk_score < 0.5
    assert review.acceptance_criteria_coverage
    assert all(review.acceptance_criteria_coverage.values())
    assert execution.id in review.evidence_refs
    assert packet.id in review.evidence_refs


def test_blocked_review_records_high_risk_uncovered_criteria_and_next_ticket_hint(
    tmp_path: Path,
) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    packet = store.load_build_packet(ticket.build_packet_id)
    execution = ExecutionResult(
        id="execution_review_blocked",
        ticket_id=ticket.id,
        backend_name="codex",
        dry_run=False,
        command="codex exec",
        blocked=True,
        block_reason="not logged in",
        failure_reason=FailureReason.AUTHENTICATION_FAILED,
        exit_code=1,
        test_exit_code=None,
        changed_files=[],
        stderr="not logged in",
    )

    review = review_execution(store, ticket, packet, execution)

    assert review.verdict is ReviewVerdict.BLOCKED
    assert review.risk_score == 1.0
    assert review.acceptance_criteria_coverage
    assert not any(review.acceptance_criteria_coverage.values())
    assert "Resolve blocker evidence and rerun the ticket." in review.next_ticket_suggestions
    assert FailureReason.AUTHENTICATION_FAILED in review.failure_reasons


def test_llm_review_missing_key_preserves_baseline_evidence_fields(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    packet = store.load_build_packet(ticket.build_packet_id)
    execution = ExecutionResult(
        id="execution_review_llm",
        ticket_id=ticket.id,
        backend_name="codex",
        dry_run=False,
        command="codex exec",
        exit_code=0,
        test_exit_code=0,
        changed_files=["demo_todo/cli.py", "tests/test_cli.py"],
        git_diff="diff --git a/tests/test_cli.py b/tests/test_cli.py",
    )

    review = review_execution_with_llm(store, ticket, packet, execution)

    assert review.verdict is ReviewVerdict.BLOCKED
    assert review.reviewer_mode == "llm_blocked"
    assert review.risk_score == 1.0
    assert execution.id in review.evidence_refs
    assert all(review.acceptance_criteria_coverage.values())


def test_llm_review_accepts_extra_report_fields_from_model(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    packet = store.load_build_packet(ticket.build_packet_id)
    execution = ExecutionResult(
        id="execution_review_llm_extra",
        ticket_id=ticket.id,
        backend_name="codex",
        dry_run=False,
        command="codex exec",
        exit_code=0,
        test_exit_code=0,
        changed_files=["demo_todo/cli.py", "tests/test_cli.py"],
        git_diff="diff --git a/tests/test_cli.py b/tests/test_cli.py",
    )

    review = review_execution_with_llm(
        store,
        ticket,
        packet,
        execution,
        client=DeepSeekClient(api_key="test-secret-key", transport=_ReviewTransport()),
    )

    assert review.reviewer_mode == "llm"
    assert review.verdict is ReviewVerdict.PASS
    assert "LLM reviewer completed" in review.passed_checks
