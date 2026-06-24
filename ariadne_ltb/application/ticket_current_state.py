from __future__ import annotations

from dataclasses import dataclass

from ariadne_ltb.application.work_truth import reduce_work_truth
from ariadne_ltb.models import AssignmentStatus, BuildTicket, ExecutionResult, InboxStatus, ReviewReport
from ariadne_ltb.storage import AriadneStore


@dataclass(frozen=True)
class TicketCurrentState:
    current_state: str
    current_assignment_id: str | None = None
    current_run_id: str | None = None
    current_execution_result_id: str | None = None
    current_review_report_id: str | None = None
    historical_blocker_count: int = 0
    active_blocker_count: int = 0
    superseded_inbox_item_ids: list[str] | None = None


def build_ticket_current_state(store: AriadneStore, ticket: BuildTicket) -> TicketCurrentState:
    execution = _latest_execution(store, ticket)
    review = _latest_review(store, ticket)
    assignment = store.find_latest_assignment_for_ticket(ticket.id)
    success = _is_success(ticket, execution, review)
    blocker_assignments = [
        item
        for item in store.list_assignments_for_ticket(ticket.id)
        if item.status in {AssignmentStatus.BLOCKED, AssignmentStatus.FAILED}
    ]
    open_inbox = [
        item
        for item in store.list_inbox_items()
        if item.ticket_id == ticket.id and item.status is InboxStatus.OPEN and getattr(item, "active", True)
    ]
    truth = reduce_work_truth(assignment=assignment, execution=execution, review=review)
    if truth.terminal_verdict in {"blocked_before_execution", "executed_failed", "review_blocked"} or blocker_assignments or open_inbox:
        active_blockers = len(blocker_assignments) + len(open_inbox)
        historical_blockers = 0
        state = "current_blocked"
    elif success:
        active_blockers = 0
        historical_blockers = len(blocker_assignments) + len(open_inbox)
        state = "current_success"
    else:
        active_blockers = 0
        historical_blockers = 0
        state = "needs_attention"
    return TicketCurrentState(
        current_state=state,
        current_assignment_id=assignment.id if assignment else None,
        current_run_id=execution.run_id if execution else None,
        current_execution_result_id=execution.id if execution else ticket.metadata.get("execution_result_id"),
        current_review_report_id=review.id if review else ticket.metadata.get("review_report_id"),
        historical_blocker_count=historical_blockers,
        active_blocker_count=active_blockers,
        superseded_inbox_item_ids=[item.id for item in open_inbox] if success else [],
    )


def _latest_execution(store: AriadneStore, ticket: BuildTicket) -> ExecutionResult | None:
    result_id = ticket.metadata.get("execution_result_id")
    if result_id:
        try:
            return store.load_execution_result(result_id)
        except FileNotFoundError:
            pass
    results = [result for result in store.list_execution_results() if result.ticket_id == ticket.id]
    return sorted(results, key=lambda item: item.ended_at)[-1] if results else None


def _latest_review(store: AriadneStore, ticket: BuildTicket) -> ReviewReport | None:
    review_id = ticket.metadata.get("review_report_id")
    if review_id:
        try:
            return store.load_review_report(review_id)
        except FileNotFoundError:
            pass
    reports = [report for report in store.list_review_reports() if report.ticket_id == ticket.id]
    return sorted(reports, key=lambda item: item.created_at)[-1] if reports else None


def _is_success(ticket: BuildTicket, execution: ExecutionResult | None, review: ReviewReport | None) -> bool:
    if execution is None or review is None:
        return False
    return (
        ticket.status.value == "done"
        and not execution.blocked
        and execution.exit_code == 0
        and execution.test_exit_code in {None, 0}
        and review.verdict.value == "pass"
    )
