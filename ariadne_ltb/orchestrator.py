from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ariadne_ltb.board import export_board
from ariadne_ltb.execution import backend_for_name
from ariadne_ltb.memory import generate_feishu_plan, write_memory_record
from ariadne_ltb.models import (
    AgentRun,
    AgentRunStatus,
    Artifact,
    ArtifactType,
    ExecutionContext,
    ExecutionResult,
    FeishuWritePlan,
    MemoryRecord,
    ReviewVerdict,
    TicketStatus,
    stable_id,
)
from ariadne_ltb.next_tickets import generate_next_tickets_artifact
from ariadne_ltb.planner import planner_for_name
from ariadne_ltb.review import review_execution
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project, target_test_command


@dataclass(frozen=True)
class TicketRunResult:
    ticket_id: str
    ticket_key: str
    backend_name: str
    planner_name: str
    build_packet_id: str
    handoff_artifact_id: str
    execution_result_id: str
    review_report_id: str
    review_verdict: str
    changed_files: list[str]
    test_exit_code: int | None
    memory_record_id: str
    memory_path: str
    feishu_plan_id: str
    feishu_plan_path: str
    next_tickets_path: str
    board_path: str
    board_html_path: str


class TicketRunOrchestrator:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def run_ticket(
        self,
        ticket_id_or_key: str,
        backend_name: str = "fake-codex",
        target_repo_path: str | None = None,
        command: str | None = None,
        planner: str = "deterministic",
        confirm_execution: bool = False,
    ) -> TicketRunResult:
        ticket = self.store.resolve_ticket(ticket_id_or_key)
        ticket = ticket.with_status(TicketStatus.PLANNING, "Build Lead")
        self.store.save_ticket(ticket)

        planner_result = planner_for_name(planner).plan_ticket(self.store, ticket)
        if not planner_result.succeeded:
            board_path = export_board(self.store)
            msg = planner_result.error or "planner failed"
            raise RuntimeError(f"{planner} planner failed for {ticket.key}: {msg}; board: {board_path}")

        ticket = self.store.load_ticket(ticket.id)
        packet = self.store.load_build_packet(planner_result.build_packet_id or ticket.build_packet_id)
        handoff_artifact = self.store.load_artifact(planner_result.handoff_artifact_id)
        handoff_prompt = self.store.read_artifact_text(handoff_artifact)

        target_repo = Path(target_repo_path).resolve() if target_repo_path else ensure_demo_target_project(self.store.root)
        execution_run = _start_run(self.store, ticket, "Execution", "execution", backend_name)
        context = ExecutionContext(
            ticket_id=ticket.id,
            ticket_key=ticket.key,
            build_packet_id=packet.id,
            target_repo_path=str(target_repo),
            handoff_prompt=handoff_prompt,
            handoff_file=str(self.store.base / "handoffs" / f"{ticket.key}.md"),
            backend_name=backend_name,
            allowed_paths=packet.affected_modules,
            command=command or (packet.tasks[0] if packet.tasks else ticket.title),
            test_command=target_test_command(),
            confirm_execution=confirm_execution,
            timeout_seconds=60,
        )
        execution = backend_for_name(backend_name).execute(context)
        self.store.save_execution_result(execution)
        execution_artifacts = _write_execution_artifacts(self.store, execution_run.id, execution)
        execution = execution.model_copy(
            update={
                "execution_log_artifact_id": execution_artifacts["execution_log"].id,
                "diff_artifact_id": execution_artifacts["git_diff"].id,
            }
        )
        self.store.save_execution_result(execution)
        execution_status = (
            AgentRunStatus.BLOCKED
            if execution.blocked
            else AgentRunStatus.SUCCEEDED
            if execution.exit_code == 0 and (execution.test_exit_code in {0, None})
            else AgentRunStatus.FAILED
        )
        execution_run = _finish_run(
            self.store,
            execution_run,
            execution_status,
            _execution_summary(execution),
            [artifact.id for artifact in execution_artifacts.values()],
        )
        ticket = (
            self.store.load_ticket(ticket.id)
            .with_run(execution_run.id)
            .with_artifacts(list(execution_artifacts.values()))
            .with_status(TicketStatus.REVIEWING, "Execution")
        )
        ticket = ticket.model_copy(
            deep=True,
            update={"metadata": ticket.metadata | {"execution_result_id": execution.id}},
        )
        self.store.save_ticket(ticket)

        review_run = _start_run(self.store, ticket, "Reviewer", "reviewer")
        review = review_execution(self.store, ticket, packet, execution)
        self.store.save_review_report(review)
        review_artifact = self.store.write_artifact(
            ticket.id,
            review_run.id,
            ArtifactType.REVIEW_REPORT,
            "review_report.json",
            review.model_dump_json(indent=2) + "\n",
            f"Reviewer verdict: {review.verdict.value}",
            metadata={"review_report_id": review.id},
        )
        review_run = _finish_run(
            self.store,
            review_run,
            AgentRunStatus.SUCCEEDED,
            f"Reviewer verdict: {review.verdict.value}.",
            [review_artifact.id],
        )
        ticket = self.store.load_ticket(ticket.id).with_run(review_run.id).with_artifacts([review_artifact])
        ticket = ticket.model_copy(
            deep=True,
            update={"metadata": ticket.metadata | {"review_report_id": review.id}},
        )
        ticket = ticket.with_status(_status_for_review(review.verdict), "Reviewer")
        self.store.save_ticket(ticket)

        memory_run = _start_run(self.store, ticket, "Memory / Feishu", "memory_feishu")
        memory, memory_path = write_memory_record(self.store, ticket, packet, execution, review)
        feishu_plan, feishu_path = generate_feishu_plan(self.store, ticket, packet, execution, review)
        memory_artifact = _write_memory_artifact(self.store, ticket.id, memory_run.id, memory, memory_path)
        feishu_artifact = _write_feishu_artifact(self.store, ticket.id, memory_run.id, feishu_plan, feishu_path)
        next_tickets_artifact = generate_next_tickets_artifact(
            self.store,
            ticket,
            packet,
            execution,
            review,
            memory_run.id,
        )
        memory_run = _finish_run(
            self.store,
            memory_run,
            AgentRunStatus.SUCCEEDED,
            "Wrote local memory, Feishu dry-run plan, and next ticket suggestions.",
            [memory_artifact.id, feishu_artifact.id, next_tickets_artifact.id],
        )
        final_status = TicketStatus.DONE if review.verdict is ReviewVerdict.PASS else _status_for_review(review.verdict)
        ticket = (
            self.store.load_ticket(ticket.id)
            .with_run(memory_run.id)
            .with_artifacts([memory_artifact, feishu_artifact, next_tickets_artifact])
            .with_status(final_status, "Memory / Feishu")
        )
        ticket = ticket.model_copy(
            deep=True,
            update={
                "metadata": ticket.metadata
                | {
                    "memory_record_id": memory.id,
                    "memory_path": str(memory_path),
                    "feishu_write_plan_id": feishu_plan.id,
                    "feishu_plan_path": str(feishu_path),
                    "next_tickets_path": next_tickets_artifact.path,
                    "selected_for_execution": True,
                    "backend_name": backend_name,
                    "external_execution_enabled": __import__("os").environ.get(
                        "ARIADNE_ENABLE_EXTERNAL_EXECUTION"
                    )
                    == "1",
                },
            },
        )
        self.store.save_ticket(ticket)
        board_path = export_board(self.store)
        return TicketRunResult(
            ticket_id=ticket.id,
            ticket_key=ticket.key,
            backend_name=backend_name,
            planner_name=planner,
            build_packet_id=packet.id,
            handoff_artifact_id=handoff_artifact.id,
            execution_result_id=execution.id,
            review_report_id=review.id,
            review_verdict=review.verdict.value,
            changed_files=execution.changed_files,
            test_exit_code=execution.test_exit_code,
            memory_record_id=memory.id,
            memory_path=str(memory_path),
            feishu_plan_id=feishu_plan.id,
            feishu_plan_path=str(feishu_path),
            next_tickets_path=next_tickets_artifact.path,
            board_path=str(board_path),
            board_html_path=str(self.store.board_dir / "index.html"),
        )


def _start_run(
    store: AriadneStore,
    ticket,
    agent_name: str,
    agent_role: str,
    backend_name: str | None = None,
) -> AgentRun:
    attempt = 1 + sum(
        1 for run_id in ticket.agent_run_ids if store.load_run(run_id).agent_role == agent_role
    )
    run = AgentRun(
        id=stable_id("run", ticket.id, agent_role, attempt),
        ticket_id=ticket.id,
        agent_name=agent_name,
        agent_role=agent_role,
        input_summary=f"{agent_name} for {ticket.key}.",
        attempt=attempt,
        backend_name=backend_name,
    ).mark_running()
    store.save_run(run)
    updated = ticket.with_run(run.id).append_event(
        "agent_run_started",
        agent_name,
        f"{agent_name} started.",
        payload_ref=run.id,
    )
    store.save_ticket(updated)
    return run


def _finish_run(
    store: AriadneStore,
    run: AgentRun,
    status: AgentRunStatus,
    summary: str,
    artifact_ids: list[str],
) -> AgentRun:
    finished = run.model_copy(update={"artifact_ids": artifact_ids}).mark_finished(status, summary)
    store.save_run(finished)
    return finished


def _write_execution_artifacts(
    store: AriadneStore,
    run_id: str,
    execution: ExecutionResult,
) -> dict[str, Artifact]:
    log = store.write_artifact(
        execution.ticket_id,
        run_id,
        ArtifactType.EXECUTION_LOG,
        "execution_log.json",
        execution.model_dump_json(indent=2) + "\n",
        "Execution stdout/stderr/exit code capture",
        metadata={"execution_result_id": execution.id},
    )
    diff = store.write_artifact(
        execution.ticket_id,
        run_id,
        ArtifactType.GIT_DIFF,
        "git_diff.patch",
        execution.git_diff or "",
        "Target project git diff",
        metadata={"execution_result_id": execution.id},
    )
    changed = store.write_artifact(
        execution.ticket_id,
        run_id,
        ArtifactType.CHANGED_FILES,
        "changed_files.json",
        json.dumps(execution.changed_files, indent=2) + "\n",
        "Changed file list",
        metadata={"execution_result_id": execution.id},
    )
    tests = store.write_artifact(
        execution.ticket_id,
        run_id,
        ArtifactType.TEST_OUTPUT,
        "test_output.json",
        json.dumps(
            {
                "test_command": execution.test_command,
                "test_exit_code": execution.test_exit_code,
                "test_stdout": execution.test_stdout,
                "test_stderr": execution.test_stderr,
            },
            indent=2,
        )
        + "\n",
        "Target project test output",
        metadata={"execution_result_id": execution.id},
    )
    return {
        "execution_log": log,
        "git_diff": diff,
        "changed_files": changed,
        "test_output": tests,
    }


def _write_memory_artifact(
    store: AriadneStore,
    ticket_id: str,
    run_id: str,
    memory: MemoryRecord,
    path: Path,
) -> Artifact:
    return store.write_artifact(
        ticket_id,
        run_id,
        ArtifactType.MEMORY_RECORD,
        "memory_record.json",
        memory.model_dump_json(indent=2) + "\n",
        "Local memory write-back record",
        metadata={"memory_record_id": memory.id, "memory_path": str(path)},
    )


def _write_feishu_artifact(
    store: AriadneStore,
    ticket_id: str,
    run_id: str,
    plan: FeishuWritePlan,
    path: Path,
) -> Artifact:
    return store.write_artifact(
        ticket_id,
        run_id,
        ArtifactType.FEISHU_WRITE_PLAN,
        "feishu_write_plan.json",
        plan.model_dump_json(indent=2) + "\n",
        "Feishu dry-run write plan",
        metadata={"feishu_write_plan_id": plan.id, "path": str(path), "dry_run": True},
    )


def _status_for_review(verdict: ReviewVerdict) -> TicketStatus:
    return {
        ReviewVerdict.PASS: TicketStatus.WRITING_MEMORY,
        ReviewVerdict.NEEDS_FIX: TicketStatus.NEEDS_FIX,
        ReviewVerdict.BLOCKED: TicketStatus.BLOCKED,
        ReviewVerdict.NEEDS_HUMAN_REVIEW: TicketStatus.WAITING_APPROVAL,
    }[verdict]


def _execution_summary(execution: ExecutionResult) -> str:
    if execution.blocked:
        return f"Execution blocked: {execution.block_reason}"
    return (
        f"Execution exit {execution.exit_code}; tests {execution.test_exit_code}; "
        f"changed {', '.join(execution.changed_files) or 'no files'}."
    )
