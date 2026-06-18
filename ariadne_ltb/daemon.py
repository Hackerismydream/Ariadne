from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from ariadne_ltb.defaults import PRODUCT_DEFAULT_BACKEND
from ariadne_ltb.failure import record_assignment_failure
from ariadne_ltb.journal import runtime_event
from ariadne_ltb.models import (
    AssignmentStatus,
    BuildTicket,
    CommentAuthorType,
    CommentKind,
    DaemonStatus,
    FailureReason,
    TicketAssignment,
    WorkerHeartbeat,
    utc_now,
)
from ariadne_ltb.orchestrator import TicketRunOrchestrator, TicketRunResult
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.llm import DeepSeekClient


@dataclass(frozen=True)
class DaemonRunResult:
    runtime_id: str
    did_work: bool
    assignment_id: str | None = None
    ticket_key: str | None = None
    status: str = "no_work"
    message: str = "no work"
    ticket_run_result: TicketRunResult | None = None


class LocalDaemonWorker:
    def __init__(self, store: AriadneStore, runtime_id: str = "local") -> None:
        self.store = store
        self.runtime_id = runtime_id

    def run_once(
        self,
        confirm_execution: bool = False,
        agent_runtime: str | None = None,
        backlog_planner: str | None = None,
        llm_agent_client: DeepSeekClient | None = None,
        timeout_seconds: int | None = None,
        assignment_id: str | None = None,
    ) -> DaemonRunResult:
        self._heartbeat(DaemonStatus.IDLE, "idle")
        assignment = self._next_assignment(assignment_id=assignment_id)
        if assignment is None:
            self._heartbeat(DaemonStatus.STOPPED, "stopped")
            message = f"assignment {assignment_id} is not claimable" if assignment_id else "no work"
            return DaemonRunResult(runtime_id=self.runtime_id, did_work=False, message=message)

        ticket = self.store.load_ticket(assignment.ticket_id)
        self._heartbeat(DaemonStatus.RUNNING, "claiming", assignment=assignment, ticket=ticket)
        claimed = assignment
        self.store.add_comment(
            ticket,
            CommentAuthorType.AGENT,
            claimed.agent_name,
            CommentKind.PROGRESS,
            f"{claimed.agent_name}: claimed {ticket.key}.",
            payload_ref=claimed.id,
            thread_id=claimed.id,
        )
        claim_event = runtime_event(
            ticket,
            self.runtime_id,
            "claim",
            "claimed",
            claimed.agent_name,
            assignment_id=claimed.id,
            payload_ref=claimed.id,
            metadata={
                "claimed_by_runtime_id": claimed.claimed_by_runtime_id,
                "lease_expires_at": claimed.lease_expires_at,
                "lease_reclaimed_at": claimed.metadata.get("lease_reclaimed_at"),
            },
        )
        self.store.append_runtime_event(claim_event)
        self._heartbeat(
            DaemonStatus.RUNNING,
            "claiming",
            assignment=claimed,
            ticket=ticket,
            last_event_id=claim_event.id,
        )

        running = claimed.mark_running()
        self.store.save_assignment(running)
        start_event = runtime_event(
            ticket,
            self.runtime_id,
            "execution",
            "started",
            running.agent_name,
            assignment_id=running.id,
        )
        self.store.append_runtime_event(start_event)
        self._heartbeat(
            DaemonStatus.RUNNING,
            "execution",
            assignment=running,
            ticket=ticket,
            last_event_id=start_event.id,
        )
        try:
            result = TicketRunOrchestrator(
                self.store,
                runtime_id=self.runtime_id,
                assignment_id=running.id,
                actor_name=running.agent_name,
            ).run_ticket(
                ticket.key,
                backend_name=running.backend_name or PRODUCT_DEFAULT_BACKEND,
                planner=running.planner_name,
                agent_runtime=agent_runtime or running.agent_runtime,
                backlog_planner=backlog_planner or running.backlog_planner_name,
                llm_agent_client=llm_agent_client,
                confirm_execution=confirm_execution,
                isolate_worktree=True,
                timeout_seconds=timeout_seconds or 60,
            )
        except Exception as exc:  # pragma: no cover - defensive, tested through blocked result path
            failure = record_assignment_failure(
                self.store,
                ticket,
                running,
                AssignmentStatus.FAILED,
                str(exc),
                FailureReason.AGENT_ERROR,
                self.runtime_id,
                actor=running.agent_name,
                stage="execution",
            )
            self._heartbeat(
                DaemonStatus.FAILED,
                "failed",
                assignment=failure.assignment,
                ticket=ticket,
                last_event_id=failure.event_id,
                last_error=failure.assignment.blocker,
            )
            return DaemonRunResult(
                runtime_id=self.runtime_id,
                did_work=True,
                assignment_id=running.id,
                ticket_key=ticket.key,
                status=failure.assignment.status.value,
                message=str(exc),
            )

        execution = self.store.load_execution_result(result.execution_result_id)
        if execution.blocked:
            failure = record_assignment_failure(
                self.store,
                ticket,
                running,
                AssignmentStatus.BLOCKED,
                execution.block_reason or "Execution backend blocked.",
                execution.failure_reason or FailureReason.UNKNOWN,
                self.runtime_id,
                actor=running.agent_name,
                stage="execution",
            )
            self._heartbeat(
                DaemonStatus.BLOCKED,
                "blocked",
                assignment=failure.assignment,
                ticket=ticket,
                last_event_id=failure.event_id,
                last_error=failure.assignment.blocker,
            )
        elif result.review_verdict == "pass":
            done = running.mark_done(
                {
                    "execution_result_id": result.execution_result_id,
                    "review_report_id": result.review_report_id,
                    "board_path": result.board_path,
                }
            )
            self.store.save_assignment(done)
            self.store.add_comment(
                ticket,
                CommentAuthorType.AGENT,
                done.agent_name,
                CommentKind.PROGRESS,
                f"{done.agent_name}: assignment done for {ticket.key}.",
                payload_ref=done.id,
                thread_id=done.id,
            )
            done_event = runtime_event(
                ticket,
                self.runtime_id,
                "assignment",
                "succeeded",
                done.agent_name,
                assignment_id=done.id,
                payload_ref=done.id,
            )
            self.store.append_runtime_event(done_event)
            self._heartbeat(
                DaemonStatus.RUNNING,
                "done",
                assignment=done,
                ticket=ticket,
                last_event_id=done_event.id,
            )
        else:
            failure = record_assignment_failure(
                self.store,
                ticket,
                running,
                AssignmentStatus.BLOCKED,
                f"Reviewer verdict: {result.review_verdict}.",
                FailureReason.REVIEW_FAILED,
                self.runtime_id,
                actor=running.agent_name,
                stage="review",
            )
            self._heartbeat(
                DaemonStatus.BLOCKED,
                "blocked",
                assignment=failure.assignment,
                ticket=ticket,
                last_event_id=failure.event_id,
                last_error=failure.assignment.blocker,
            )

        latest = self.store.load_assignment(running.id)
        self._heartbeat(
            DaemonStatus.STOPPED,
            "stopped",
            assignment=latest,
            ticket=ticket,
        )
        return DaemonRunResult(
            runtime_id=self.runtime_id,
            did_work=True,
            assignment_id=latest.id,
            ticket_key=ticket.key,
            status=latest.status.value,
            message=f"assignment {latest.status.value}",
            ticket_run_result=result,
        )

    def run_loop(
        self,
        interval_seconds: float = 5.0,
        max_iterations: int | None = None,
        confirm_execution: bool = False,
        agent_runtime: str | None = None,
        backlog_planner: str | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        iterations = 0
        while max_iterations is None or iterations < max_iterations:
            self.run_once(
                confirm_execution=confirm_execution,
                agent_runtime=agent_runtime,
                backlog_planner=backlog_planner,
                timeout_seconds=timeout_seconds,
            )
            iterations += 1
            if max_iterations is not None and iterations >= max_iterations:
                break
            time.sleep(interval_seconds)

    def _next_assignment(self, assignment_id: str | None = None) -> TicketAssignment | None:
        if assignment_id:
            return self.store.claim_assignment(assignment_id, self.runtime_id)
        return self.store.claim_next_assignment(self.runtime_id)

    def _heartbeat(
        self,
        status: DaemonStatus,
        stage: str,
        assignment: TicketAssignment | None = None,
        ticket: BuildTicket | None = None,
        last_event_id: str | None = None,
        last_error: str | None = None,
    ) -> WorkerHeartbeat:
        try:
            existing = self.store.load_worker_heartbeat(self.runtime_id)
            started_at = existing.started_at
        except FileNotFoundError:
            started_at = utc_now()
        heartbeat = WorkerHeartbeat(
            runtime_id=self.runtime_id,
            pid=os.getpid(),
            status=status,
            current_assignment_id=assignment.id if assignment else None,
            current_ticket_id=ticket.id if ticket else None,
            current_ticket_key=ticket.key if ticket else None,
            current_stage=stage,
            started_at=started_at,
            heartbeat_at=utc_now(),
            last_event_id=last_event_id,
            last_error=last_error,
        )
        self.store.save_worker_heartbeat(heartbeat)
        return heartbeat


def is_stale_heartbeat(
    heartbeat: WorkerHeartbeat,
    stale_after_seconds: int = 120,
) -> bool:
    try:
        heartbeat_at = datetime.fromisoformat(heartbeat.heartbeat_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    if (datetime.now(UTC) - heartbeat_at).total_seconds() > stale_after_seconds:
        return True
    try:
        os.kill(heartbeat.pid, 0)
    except OSError:
        return True
    return False
