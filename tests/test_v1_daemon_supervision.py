from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.daemon import LocalDaemonWorker, is_stale_heartbeat
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import AssignmentStatus, DaemonStatus, ExecutionResult, FailureReason, WorkerHeartbeat
from ariadne_ltb.orchestrator import TicketRunOrchestrator, TicketRunResult
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project
from tests.helpers import ready_assignment_with_handoff


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_run_once_writes_worker_heartbeat(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    runner = CliRunner()
    assign = runner.invoke(
        app,
        ["--root", str(tmp_path), "ticket", "assign", "ARI-003", "--to", "fake-codex"],
    )
    assert assign.exit_code == 0, assign.output

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "daemon", "run-once", "--runtime-id", "test-worker"],
    )

    heartbeat = store.load_worker_heartbeat("test-worker")
    assert result.exit_code == 0, result.output
    assert heartbeat.runtime_id == "test-worker"
    assert heartbeat.status in {DaemonStatus.STOPPED, DaemonStatus.IDLE, DaemonStatus.RUNNING}
    assert heartbeat.current_assignment_id
    assert heartbeat.current_ticket_key == "ARI-003"
    assert heartbeat.current_stage in {"done", "board", "stopped"}


def test_run_once_can_claim_specific_assignment(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    runner = CliRunner()
    first = runner.invoke(
        app,
        ["--root", str(tmp_path), "ticket", "assign", "ARI-003", "--to", "fake-codex"],
    )
    second = runner.invoke(
        app,
        ["--root", str(tmp_path), "ticket", "assign", "ARI-003", "--to", "fake-codex"],
    )
    first_id = _assignment_id_from_output(first.output)
    second_id = _assignment_id_from_output(second.output)

    result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "daemon",
            "run-once",
            "--assignment-id",
            second_id,
        ],
    )

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    assert result.exit_code == 0, result.output
    assert f"Assignment claimed: {second_id}" in result.output
    assert store.load_assignment(first_id).status.value == "ready_to_claim"
    assert store.load_assignment(second_id).status.value == "done"


def test_daemon_status_shows_heartbeat_and_counts(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    heartbeat = WorkerHeartbeat.new(runtime_id="visible-worker", status=DaemonStatus.IDLE)
    store.save_worker_heartbeat(heartbeat)

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "daemon", "status"])

    assert result.exit_code == 0, result.output
    assert "runtime_id: visible-worker" in result.output
    assert "status: idle" in result.output
    assert "stale:" in result.output
    assert "open assignments:" in result.output


def test_list_worker_heartbeats_ignores_partial_or_invalid_files(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    store.save_worker_heartbeat(WorkerHeartbeat.new(runtime_id="valid-worker", status=DaemonStatus.IDLE))
    (tmp_path / ".ariadne" / "daemon" / "heartbeats" / "partial.json").write_text("", encoding="utf-8")

    heartbeats = store.list_worker_heartbeats()

    assert [heartbeat.runtime_id for heartbeat in heartbeats] == ["valid-worker"]


def test_stale_heartbeat_by_old_timestamp_and_dead_pid() -> None:
    heartbeat = WorkerHeartbeat(
        runtime_id="stale-worker",
        pid=999999,
        status=DaemonStatus.RUNNING,
        started_at="2000-01-01T00:00:00Z",
        heartbeat_at="2000-01-01T00:00:00Z",
    )

    assert is_stale_heartbeat(heartbeat, stale_after_seconds=1) is True


def test_run_once_recovers_stale_assignment_for_same_runtime(monkeypatch, tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    assignment = ready_assignment_with_handoff(
        store,
        ticket,
        store.create_assignment(ticket, store.resolve_agent_profile("fake-codex")),
        ensure_demo_target_project(tmp_path),
    )
    running = assignment.mark_claimed("stale-worker").mark_running()
    store.save_assignment(running)
    store.save_worker_heartbeat(
        WorkerHeartbeat(
            runtime_id="stale-worker",
            pid=999999,
            status=DaemonStatus.RUNNING,
            current_assignment_id=running.id,
            current_ticket_id=ticket.id,
            current_ticket_key=ticket.key,
            current_stage="execution",
            started_at="2000-01-01T00:00:00Z",
            heartbeat_at="2000-01-01T00:00:00Z",
        )
    )

    def pass_run(orchestrator, *args, **kwargs):  # type: ignore[no-untyped-def]
        execution = ExecutionResult(
            id="execution_recovered",
            ticket_id=ticket.id,
            backend_name="fake-codex",
            dry_run=True,
            command="fake-codex",
            exit_code=0,
            assignment_id=orchestrator.assignment_id,
        )
        store.save_execution_result(execution)
        return _ticket_run_result(ticket, execution.id, review_verdict="pass")

    monkeypatch.setattr(TicketRunOrchestrator, "run_ticket", pass_run)

    result = LocalDaemonWorker(store, runtime_id="stale-worker").run_once()

    updated = store.load_assignment(assignment.id)
    events = store.list_runtime_events_for_ticket(ticket.id)
    assert result.did_work is True
    assert result.status == "done"
    assert updated.status is AssignmentStatus.DONE
    assert updated.metadata["retry_count"] == 1
    assert any(event.stage == "recovery" and event.event_type == "orphan_requeued" for event in events)


def test_run_once_auto_retries_safe_failures_until_limit(monkeypatch, tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    assignment = ready_assignment_with_handoff(
        store,
        ticket,
        store.create_assignment(ticket, store.resolve_agent_profile("fake-codex")),
        ensure_demo_target_project(tmp_path),
    )
    calls = 0

    def blocked_run(orchestrator, *args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal calls
        calls += 1
        execution = ExecutionResult(
            id=f"execution_retry_{calls}",
            ticket_id=ticket.id,
            backend_name="codex",
            dry_run=False,
            blocked=True,
            block_reason="codex command is missing",
            failure_reason=FailureReason.COMMAND_UNAVAILABLE,
            command="codex exec",
            exit_code=127,
            assignment_id=orchestrator.assignment_id,
        )
        store.save_execution_result(execution)
        return _ticket_run_result(ticket, execution.id, review_verdict="fail")

    monkeypatch.setattr(TicketRunOrchestrator, "run_ticket", blocked_run)

    first = LocalDaemonWorker(store, runtime_id="retry-worker").run_once()
    first_assignment = store.load_assignment(assignment.id)
    second = LocalDaemonWorker(store, runtime_id="retry-worker").run_once()
    second_assignment = store.load_assignment(assignment.id)
    third = LocalDaemonWorker(store, runtime_id="retry-worker").run_once()
    final_assignment = store.load_assignment(assignment.id)
    retry_events = [
        event
        for event in store.list_runtime_events_for_ticket(ticket.id)
        if event.stage == "retry" and event.event_type == "auto_retry_queued"
    ]

    assert first.status == "queued"
    assert first_assignment.status is AssignmentStatus.QUEUED
    assert first_assignment.metadata["retry_count"] == 1
    assert second.status == "queued"
    assert second_assignment.status is AssignmentStatus.QUEUED
    assert second_assignment.metadata["retry_count"] == 2
    assert third.status == "blocked"
    assert final_assignment.status is AssignmentStatus.BLOCKED
    assert final_assignment.failure_reason is FailureReason.COMMAND_UNAVAILABLE
    assert final_assignment.metadata["retry_count"] == 2
    assert len(retry_events) == 2


def test_daemon_start_max_iterations_does_not_block(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "daemon",
            "start",
            "--runtime-id",
            "loop-test",
            "--max-iterations",
            "1",
            "--interval",
            "0",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "daemon loop finished" in result.output
    data = json.loads(
        (tmp_path / ".ariadne" / "daemon" / "heartbeats" / "loop-test.json").read_text(
            encoding="utf-8"
        )
    )
    assert data["runtime_id"] == "loop-test"


def _assignment_id_from_output(output: str) -> str:
    for line in output.splitlines():
        if line.startswith("Assignment created:"):
            return line.split(":", 1)[1].strip()
    raise AssertionError(output)


def _ticket_run_result(
    ticket,
    execution_result_id: str,
    review_verdict: str,
) -> TicketRunResult:
    return TicketRunResult(
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        backend_name="fake-codex",
        planner_name="deterministic",
        agent_runtime="deterministic",
        build_packet_id=ticket.build_packet_id or "packet",
        handoff_artifact_id="handoff_artifact",
        execution_result_id=execution_result_id,
        review_report_id="review_report",
        review_verdict=review_verdict,
        changed_files=[],
        test_exit_code=None,
        memory_record_id="memory",
        memory_path="memory.json",
        feishu_plan_id="feishu",
        feishu_plan_path="feishu.json",
        next_tickets_path="next_tickets.json",
        backlog_planner_name="deterministic",
        backlog_planner_artifact_path=None,
        llm_agent_artifact_paths=[],
        backlog_preview_ids=[],
        backlog_update_ids=[],
        board_path="board.md",
        board_html_path="board.html",
        orchestrator_result_path="orchestrator_result.json",
        landing_evidence_json_path="landing_evidence.json",
        landing_evidence_md_path="landing_evidence.md",
    )
