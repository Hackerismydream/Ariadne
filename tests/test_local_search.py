from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.inbox import refresh_inbox
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import (
    ArtifactType,
    CommentAuthorType,
    CommentKind,
    ExecutionResult,
    FailureReason,
    FeishuWriteResult,
    MemoryRecord,
    ReviewReport,
    ReviewVerdict,
)
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_local_search_indexes_tickets_comments_memory_artifacts_reviews_and_integrations(
    tmp_path: Path,
) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    ticket = ticket.model_copy(update={"description": f"{ticket.description}\nauth quota ticket evidence"})
    store.save_ticket(ticket)
    store.add_comment(
        ticket,
        CommentAuthorType.AGENT,
        "Reviewer",
        CommentKind.BLOCKER,
        "auth quota blocker from provider",
    )
    store.save_memory_record(
        MemoryRecord(
            id="memory_search",
            ticket_id=ticket.id,
            title="Searchable memory auth quota",
            decision_log_entry="auth quota recovery memory",
            build_summary="memory summary",
            review_summary="review summary",
        )
    )
    store.save_review_report(
        ReviewReport(
            id="review_search",
            ticket_id=ticket.id,
            verdict=ReviewVerdict.BLOCKED,
            failed_checks=["auth quota check failed"],
            failure_reasons=[FailureReason.QUOTA_EXCEEDED],
        )
    )
    store.write_artifact(
        ticket.id,
        "run_search",
        ArtifactType.EXECUTION_LOG,
        "execution_log.txt",
        "auth quota artifact evidence",
        "search artifact",
    )
    store.save_execution_result(
        ExecutionResult(
            id="execution_search",
            ticket_id=ticket.id,
            backend_name="codex",
            dry_run=False,
            blocked=True,
            block_reason="auth quota execution evidence",
            failure_reason=FailureReason.QUOTA_EXCEEDED,
            command="codex exec",
            exit_code=1,
            stderr="auth quota",
        )
    )
    feishu_result = FeishuWriteResult(
        id="feishu_search",
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        plan_id="feishu_plan_search",
        ok=False,
        blocked=True,
        dry_run=True,
        failure_reason=FailureReason.QUOTA_EXCEEDED,
        reason="feishu auth quota",
        operation_summary="feishu auth quota write result",
    )
    store.save_feishu_write_result(feishu_result)
    refresh_inbox(store)

    result = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "search", "auth quota", "--output", "json", "--limit", "30"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    kinds = {item["kind"] for item in payload}
    assert {
        "ticket",
        "comment",
        "memory",
        "artifact",
        "review",
        "execution",
        "feishu",
        "inbox",
    }.issubset(kinds)
    assert all("source_ref" in item for item in payload)


def test_local_search_cli_table_reports_no_matches(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["--root", str(tmp_path), "search", "nothing"])

    assert result.exit_code == 0, result.output
    assert "No local search matches." in result.output
