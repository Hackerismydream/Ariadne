from __future__ import annotations

import time
from dataclasses import dataclass

from ariadne_ltb.journal import runtime_event
from ariadne_ltb.models import (
    AssignmentStatus,
    CommentAuthorType,
    CommentKind,
    FailureReason,
    TicketAssignment,
)
from ariadne_ltb.orchestrator import TicketRunOrchestrator, TicketRunResult
from ariadne_ltb.storage import AriadneStore


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

    def run_once(self, confirm_execution: bool = False) -> DaemonRunResult:
        assignment = self._next_assignment()
        if assignment is None:
            return DaemonRunResult(runtime_id=self.runtime_id, did_work=False)

        ticket = self.store.load_ticket(assignment.ticket_id)
        claimed = assignment.mark_claimed(self.runtime_id)
        self.store.save_assignment(claimed)
        self.store.add_comment(
            ticket,
            CommentAuthorType.AGENT,
            claimed.agent_name,
            CommentKind.PROGRESS,
            f"{claimed.agent_name}: claimed {ticket.key}.",
            payload_ref=claimed.id,
        )
        self.store.append_runtime_event(
            runtime_event(
                ticket,
                self.runtime_id,
                "claim",
                "claimed",
                claimed.agent_name,
                assignment_id=claimed.id,
                payload_ref=claimed.id,
            )
        )

        running = claimed.mark_running()
        self.store.save_assignment(running)
        self.store.append_runtime_event(
            runtime_event(
                ticket,
                self.runtime_id,
                "execution",
                "started",
                running.agent_name,
                assignment_id=running.id,
            )
        )
        try:
            result = TicketRunOrchestrator(
                self.store,
                runtime_id=self.runtime_id,
                assignment_id=running.id,
                actor_name=running.agent_name,
            ).run_ticket(
                ticket.key,
                backend_name=running.backend_name or "fake-codex",
                planner=running.planner_name,
                confirm_execution=confirm_execution,
            )
        except Exception as exc:  # pragma: no cover - defensive, tested through blocked result path
            blocked = running.mark_failed(str(exc), FailureReason.AGENT_ERROR)
            self.store.save_assignment(blocked)
            self._write_blocker(ticket, blocked, str(exc))
            return DaemonRunResult(
                runtime_id=self.runtime_id,
                did_work=True,
                assignment_id=running.id,
                ticket_key=ticket.key,
                status=blocked.status.value,
                message=str(exc),
            )

        execution = self.store.load_execution_result(result.execution_result_id)
        if execution.blocked:
            blocked = running.mark_blocked(
                execution.block_reason or "Execution backend blocked.",
                execution.failure_reason or FailureReason.UNKNOWN,
            )
            self.store.save_assignment(blocked)
            self._write_blocker(ticket, blocked, blocked.blocker or "Execution blocked.")
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
            )
            self.store.append_runtime_event(
                runtime_event(
                    ticket,
                    self.runtime_id,
                    "assignment",
                    "succeeded",
                    done.agent_name,
                    assignment_id=done.id,
                    payload_ref=done.id,
                )
            )
        else:
            blocked = running.mark_blocked(
                f"Reviewer verdict: {result.review_verdict}.",
                FailureReason.REVIEW_FAILED,
            )
            self.store.save_assignment(blocked)
            self._write_blocker(ticket, blocked, blocked.blocker or "Review blocked.")

        latest = self.store.load_assignment(running.id)
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
    ) -> None:
        iterations = 0
        while max_iterations is None or iterations < max_iterations:
            self.run_once(confirm_execution=confirm_execution)
            iterations += 1
            if max_iterations is not None and iterations >= max_iterations:
                break
            time.sleep(interval_seconds)

    def _next_assignment(self) -> TicketAssignment | None:
        open_assignments = [
            assignment
            for assignment in self.store.list_open_assignments()
            if assignment.status is AssignmentStatus.QUEUED
        ]
        if not open_assignments:
            return None
        return sorted(open_assignments, key=lambda item: item.created_at)[0]

    def _write_blocker(self, ticket, assignment: TicketAssignment, body: str) -> None:  # type: ignore[no-untyped-def]
        self.store.add_comment(
            ticket,
            CommentAuthorType.AGENT,
            assignment.agent_name,
            CommentKind.BLOCKER,
            f"{assignment.agent_name}: blocked - {body}",
            payload_ref=assignment.id,
        )
        self.store.append_runtime_event(
            runtime_event(
                ticket,
                self.runtime_id,
                "assignment",
                "blocked",
                assignment.agent_name,
                assignment_id=assignment.id,
                payload_ref=assignment.id,
                metadata={"blocker": body},
            )
        )
