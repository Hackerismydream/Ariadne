from __future__ import annotations

from ariadne_ltb.application.assignment_control import canonicalize_duplicate_runnable_assignments
from ariadne_ltb.application.comments import CommentService
from ariadne_ltb.application.current_version_scope import current_version_mainline_tickets
from ariadne_ltb.application.daemon_control import DaemonControlService
from ariadne_ltb.application.dtos import (
    AssignTicketInput,
    AssignTicketOutput,
    CommentDTO,
    CreateCommentInput,
    DaemonControlOutput,
    IssueDetailDTO,
    IssueDetailResponse,
    IssueExecutionResultSummaryDTO,
    IssueListItemDTO,
    IssueListResponse,
    IssuePatchInput,
    IssueTimelineEventDTO,
    RunAssignmentInput,
    RunAssignmentOutput,
    TimelineDTO,
)
from ariadne_ltb.application.errors import NotFoundError, ValidationAppError
from ariadne_ltb.application.mappers import assignment_dto, comment_dto
from ariadne_ltb.application.project_versions import ProjectVersionService
from ariadne_ltb.application.run_assignment import RunAssignmentService
from ariadne_ltb.application.run_events import RunEventService
from ariadne_ltb.application.assign_ticket import AssignTicketService
from ariadne_ltb.application.workbench_artifacts import IssueEvidenceProjectionService
from ariadne_ltb.application.work_truth import reduce_work_truth
from ariadne_ltb.models import AssignmentStatus, BuildTicket, ExecutionResult, ReviewReport, TicketAssignment, TicketStatus, utc_now
from ariadne_ltb.storage import AriadneStore


class WorkbenchIssuesService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def list(self) -> IssueListResponse:
        canonicalize_duplicate_runnable_assignments(self.store)
        target_project_id, target_version = self._current_version_scope()
        context = self._list_context()
        issues = [
            self._issue_item(ticket, target_version=target_version, context=context)
            for ticket in self._current_version_mainline_tickets(target_project_id)
        ]
        return IssueListResponse(issues=issues)

    def detail(self, issue_id_or_key: str) -> IssueDetailResponse:
        ticket = self._resolve_ticket(issue_id_or_key)
        canonicalize_duplicate_runnable_assignments(self.store, ticket_id=ticket.id)
        _target_project_id, target_version = self._current_version_scope()
        item = self._issue_item(ticket, target_version=target_version)
        assignments = self.store.list_assignments_for_ticket(ticket.id)
        executions = self._executions(ticket)
        latest_execution = executions[-1] if executions else None
        review = self._latest_review(ticket)
        route_assignment = self._latest_assignment(ticket)
        route_decision = self._route_decision(route_assignment)
        handoff = self._handoff(ticket, route_assignment, latest_execution)
        evidence_sections = IssueEvidenceProjectionService(self.store).sections(
            ticket,
            assignments,
            executions,
            review,
        )
        issue = IssueDetailDTO(
            **item.model_dump(mode="python"),
            body=ticket.description,
            acceptance_criteria=self._acceptance_criteria(ticket),
            affected_modules=self._affected_modules(ticket),
            comments=[comment_dto(comment) for comment in self.store.list_comments(ticket.id)],
            timeline=self._timeline(ticket),
            assignments=[assignment_dto(assignment) for assignment in assignments],
            execution_results=[self._execution_summary(result) for result in executions],
            source_links=self._source_links(ticket),
            route_decision=route_decision,
            handoff=handoff,
            diff_summary=self._diff_summary(latest_execution),
            test_summary=self._test_summary(latest_execution),
            review_summary=self._review_summary(review),
            next_issue_links=self._next_issue_links(ticket),
            evidence_sections=evidence_sections,
        )
        return IssueDetailResponse(issue=issue)

    def patch(self, issue_id_or_key: str, payload: IssuePatchInput) -> IssueDetailResponse:
        ticket = self._resolve_ticket(issue_id_or_key)
        updated = ticket.model_copy(deep=True)
        changes: list[str] = []
        if payload.title is not None and payload.title != updated.title:
            updated.title = payload.title
            changes.append("title")
        if payload.priority is not None and payload.priority != updated.priority:
            updated.priority = payload.priority
            changes.append("priority")
        if payload.status is not None:
            try:
                next_status = TicketStatus(payload.status)
            except ValueError as exc:
                raise ValidationAppError("unknown issue status", {"status": payload.status}) from exc
            if next_status is not updated.status:
                updated = updated.with_status(next_status, "Ariadne", f"Issue status changed to {next_status.value}.")
                changes.append("status")
        if changes:
            updated = updated.append_event(
                "issue_updated",
                "Ariadne",
                f"Updated issue fields: {', '.join(changes)}.",
            )
            updated.updated_at = utc_now()
            self.store.save_ticket(updated)
        return self.detail(updated.id)

    def add_comment(self, issue_id_or_key: str, payload: CreateCommentInput) -> dict[str, CommentDTO]:
        return {"comment": CommentService(self.store).add_human_comment(issue_id_or_key, payload)}

    def timeline(self, issue_id_or_key: str) -> TimelineDTO:
        return CommentService(self.store).timeline(issue_id_or_key)

    def assign(self, issue_id_or_key: str, payload: AssignTicketInput) -> AssignTicketOutput:
        return AssignTicketService(self.store).assign(issue_id_or_key, payload, source="http")

    def rerun(self, issue_id_or_key: str, payload: RunAssignmentInput) -> RunAssignmentOutput:
        assignment = self._latest_assignment(self._resolve_ticket(issue_id_or_key))
        if assignment is None:
            raise NotFoundError("issue has no assignment to rerun", {"issue": issue_id_or_key})
        if assignment.status.is_terminal:
            raise ValidationAppError(
                "rerun_requires_assignment_id",
                {
                    "issue": issue_id_or_key,
                    "assignment_id": assignment.id,
                    "status": assignment.status.value,
                    "message": "Retry a specific failed assignment row instead of rerunning the issue latest pointer.",
                },
            )
        return RunAssignmentService(self.store).run(assignment.id, payload)

    def run_now(self, issue_id_or_key: str, payload: RunAssignmentInput) -> DaemonControlOutput:
        assignment = self._latest_assignment(self._resolve_ticket(issue_id_or_key))
        if assignment is None:
            raise NotFoundError("issue has no assignment to run", {"issue": issue_id_or_key})
        return DaemonControlService(self.store).run_now(assignment.id, payload)

    def _current_version_scope(self) -> tuple[str | None, str | None]:
        current = ProjectVersionService(self.store).current()
        if current is None:
            return None, None
        return current.target_project_id, current.version_label

    def _current_version_mainline_tickets(self, target_project_id: str | None) -> list[BuildTicket]:
        return current_version_mainline_tickets(self.store, target_project_id)

    def _resolve_ticket(self, issue_id_or_key: str) -> BuildTicket:
        try:
            return self.store.resolve_ticket(issue_id_or_key)
        except FileNotFoundError as exc:
            raise NotFoundError(f"Issue not found: {issue_id_or_key}", {"issue": issue_id_or_key}) from exc

    def _list_context(self) -> dict[str, dict[str, object]]:
        latest_assignments: dict[str, TicketAssignment] = {}
        latest_blocking_assignments: dict[str, TicketAssignment] = {}
        for assignment in self.store.list_assignments():
            current = latest_assignments.get(assignment.ticket_id)
            if current is None or assignment.created_at > current.created_at:
                latest_assignments[assignment.ticket_id] = assignment
            if assignment.status in {AssignmentStatus.BLOCKED, AssignmentStatus.FAILED}:
                current_blocker = latest_blocking_assignments.get(assignment.ticket_id)
                if current_blocker is None or self._assignment_timestamp(assignment) > self._assignment_timestamp(current_blocker):
                    latest_blocking_assignments[assignment.ticket_id] = assignment
        latest_executions: dict[str, ExecutionResult] = {}
        execution_counts: dict[str, int] = {}
        for execution in self.store.list_execution_results():
            execution_counts[execution.ticket_id] = execution_counts.get(execution.ticket_id, 0) + 1
            current_execution = latest_executions.get(execution.ticket_id)
            if current_execution is None or execution.ended_at > current_execution.ended_at:
                latest_executions[execution.ticket_id] = execution
        latest_reviews: dict[str, ReviewReport] = {}
        review_counts: dict[str, int] = {}
        for review in self.store.list_review_reports():
            review_counts[review.ticket_id] = review_counts.get(review.ticket_id, 0) + 1
            current_review = latest_reviews.get(review.ticket_id)
            if current_review is None or review.created_at > current_review.created_at:
                latest_reviews[review.ticket_id] = review
        latest_run_status: dict[str, tuple[str, str]] = {}
        for run in self.store.list_runs():
            timestamp = run.ended_at or run.started_at or ""
            current = latest_run_status.get(run.ticket_id)
            if current is None or timestamp > current[0]:
                latest_run_status[run.ticket_id] = (timestamp, run.status.value)
        return {
            "assignments": latest_assignments,
            "blocking_assignments": latest_blocking_assignments,
            "executions": latest_executions,
            "execution_counts": execution_counts,
            "reviews": latest_reviews,
            "review_counts": review_counts,
            "run_status": {ticket_id: item[1] for ticket_id, item in latest_run_status.items()},
        }

    def _issue_item(
        self,
        ticket: BuildTicket,
        target_version: str | None = None,
        context: dict[str, dict[str, object]] | None = None,
    ) -> IssueListItemDTO:
        assignment = (
            context["assignments"].get(ticket.id) if context else self._latest_assignment(ticket)
        )
        execution = (
            context["executions"].get(ticket.id) if context else self._latest_execution(ticket)
        )
        review = (
            context["reviews"].get(ticket.id) if context else self._latest_review(ticket)
        )
        run_status = (
            context["run_status"].get(ticket.id) if context else self._latest_run_status(ticket)
        )
        blocking_assignment = (
            context["blocking_assignments"].get(ticket.id)
            if context
            else self._blocking_assignment(ticket, execution if isinstance(execution, ExecutionResult) else None)
        )
        effective_assignment = self._effective_assignment(
            assignment if isinstance(assignment, TicketAssignment) else None,
            blocking_assignment if isinstance(blocking_assignment, TicketAssignment) else None,
            execution if isinstance(execution, ExecutionResult) else None,
        )
        evidence_count = (
            int(context["execution_counts"].get(ticket.id, 0))
            + int(context["review_counts"].get(ticket.id, 0))
            + len(ticket.artifact_ids)
            if context
            else self._evidence_count(ticket)
        )
        truth = reduce_work_truth(
            assignment=effective_assignment,
            execution=execution if isinstance(execution, ExecutionResult) else None,
            review=review if isinstance(review, ReviewReport) else None,
            run_status=run_status,
        )
        return IssueListItemDTO(
            id=ticket.id,
            key=ticket.key,
            title=ticket.title,
            status=ticket.status.value,
            priority=ticket.priority,
            assignee=effective_assignment.agent_name if effective_assignment else ticket.owner_agent,
            project=ticket.metadata.get("target_project_id"),
            target_version=target_version,
            source_count=len(self._source_links(ticket)),
            evidence_count=evidence_count,
            last_run_status=truth.terminal_verdict,
            terminal_verdict=truth.terminal_verdict,
            review_verdict=review.verdict.value if isinstance(review, ReviewReport) else None,
            blocked_reason=truth.blocked_reason
            or self._blocked_reason(
                ticket,
                effective_assignment,
                execution if isinstance(execution, ExecutionResult) else None,
            ),
            updated_at=ticket.updated_at or ticket.created_at,
        )

    def _latest_assignment(self, ticket: BuildTicket) -> TicketAssignment | None:
        return self.store.find_latest_assignment_for_ticket(ticket.id)

    def _blocking_assignment(
        self,
        ticket: BuildTicket,
        execution: ExecutionResult | None,
    ) -> TicketAssignment | None:
        blockers = [
            assignment
            for assignment in self.store.list_assignments_for_ticket(ticket.id)
            if assignment.status in {AssignmentStatus.BLOCKED, AssignmentStatus.FAILED}
        ]
        if not blockers:
            return None
        latest = sorted(blockers, key=self._assignment_timestamp)[-1]
        if execution is None or self._assignment_timestamp(latest) >= execution.ended_at:
            return latest
        return None

    def _effective_assignment(
        self,
        assignment: TicketAssignment | None,
        blocking_assignment: TicketAssignment | None,
        execution: ExecutionResult | None,
    ) -> TicketAssignment | None:
        if blocking_assignment is None:
            return assignment
        if execution is None or self._assignment_timestamp(blocking_assignment) >= execution.ended_at:
            return blocking_assignment
        return assignment

    def _assignment_timestamp(self, assignment: TicketAssignment) -> str:
        return assignment.ended_at or assignment.started_at or assignment.claimed_at or assignment.created_at

    def _latest_run_status(self, ticket: BuildTicket) -> str | None:
        runs = [run for run in self.store.list_runs() if run.ticket_id == ticket.id]
        if not runs:
            return None
        run = sorted(runs, key=lambda item: item.ended_at or item.started_at or "")[-1]
        return run.status.value

    def _executions(self, ticket: BuildTicket) -> list[ExecutionResult]:
        return sorted(
            [result for result in self.store.list_execution_results() if result.ticket_id == ticket.id],
            key=lambda item: item.ended_at,
        )

    def _latest_execution(self, ticket: BuildTicket) -> ExecutionResult | None:
        executions = self._executions(ticket)
        return executions[-1] if executions else None

    def _latest_review(self, ticket: BuildTicket) -> ReviewReport | None:
        reports = [report for report in self.store.list_review_reports() if report.ticket_id == ticket.id]
        return sorted(reports, key=lambda item: item.created_at)[-1] if reports else None

    def _artifact_path(self, artifact_id: str | None) -> str | None:
        if not artifact_id:
            return None
        try:
            return self.store.load_artifact(artifact_id).path
        except FileNotFoundError:
            return None

    def _execution_summary(self, result: ExecutionResult) -> IssueExecutionResultSummaryDTO:
        truth = reduce_work_truth(execution=result)
        return IssueExecutionResultSummaryDTO(
            id=result.id,
            backend_name=result.backend_name,
            blocked=result.blocked,
            failure_reason=result.failure_reason.value if result.failure_reason else None,
            exit_code=result.exit_code,
            test_exit_code=result.test_exit_code,
            changed_files=list(truth.agent_changed_files),
            preflight_dirty_files=list(truth.preflight_dirty_files),
            terminal_verdict=truth.terminal_verdict,
            diff_artifact_path=self._artifact_path(result.diff_artifact_id),
            execution_log_artifact_path=self._artifact_path(result.execution_log_artifact_id),
            started_at=result.started_at,
            ended_at=result.ended_at,
        )

    def _timeline(self, ticket: BuildTicket) -> list[IssueTimelineEventDTO]:
        events: list[IssueTimelineEventDTO] = []
        assignment_ids = {assignment.id for assignment in self.store.list_assignments_for_ticket(ticket.id)}
        for index, event in enumerate(ticket.event_log):
            events.append(
                IssueTimelineEventDTO(
                    id=f"{ticket.id}:ticket:{index}",
                    event_type=event.event_type,
                    actor=event.actor,
                    summary=event.summary,
                    timestamp=event.timestamp,
                    ref_id=event.payload_ref,
                )
            )
        for assignment_event in RunEventService(self.store).ticket_assignment_events(ticket.id):
            events.append(
                IssueTimelineEventDTO(
                    id=f"assignment-event:{assignment_event.id}",
                    event_type=f"{assignment_event.source}:{assignment_event.event_type}",
                    actor=assignment_event.actor,
                    summary=assignment_event.summary,
                    timestamp=assignment_event.timestamp,
                    ref_id=assignment_event.ref_id or assignment_event.assignment_id,
                )
            )
        for comment in self.store.list_comments(ticket.id):
            if comment.thread_id in assignment_ids or comment.payload_ref in assignment_ids:
                continue
            events.append(
                IssueTimelineEventDTO(
                    id=comment.id,
                    event_type=f"comment:{comment.kind.value}",
                    actor=comment.author,
                    summary=comment.body,
                    timestamp=comment.created_at,
                    ref_id=comment.thread_id,
                )
            )
        for event in self.store.list_runtime_events_for_ticket(ticket.id):
            if event.assignment_id in assignment_ids:
                continue
            events.append(
                IssueTimelineEventDTO(
                    id=event.id,
                    event_type=f"runtime:{event.event_type}",
                    actor=event.actor,
                    summary=f"{event.stage} {event.event_type}",
                    timestamp=event.timestamp,
                    ref_id=event.payload_ref or event.assignment_id or event.run_id,
                )
            )
        return sorted(events, key=lambda item: item.timestamp)

    def _source_links(self, ticket: BuildTicket) -> list[str]:
        links = [ticket.source_ref] if ticket.source_ref else []
        for key in ["source_document_id", "source_id", "source_artifact_id"]:
            value = ticket.metadata.get(key)
            if value:
                links.append(str(value))
        for value in ticket.metadata.get("source_artifact_ids", []) or []:
            links.append(str(value))
        return sorted(set(links))

    def _acceptance_criteria(self, ticket: BuildTicket) -> list[str]:
        values = ticket.metadata.get("acceptance_criteria")
        if isinstance(values, list):
            return [str(value) for value in values if value]
        if ticket.build_packet_id:
            try:
                return list(self.store.load_build_packet(ticket.build_packet_id).acceptance_criteria)
            except FileNotFoundError:
                return []
        return []

    def _affected_modules(self, ticket: BuildTicket) -> list[str]:
        values = ticket.metadata.get("affected_modules")
        if isinstance(values, list):
            return [str(value) for value in values if value]
        if ticket.build_packet_id:
            try:
                return list(self.store.load_build_packet(ticket.build_packet_id).affected_modules)
            except FileNotFoundError:
                return []
        return []

    def _evidence_count(self, ticket: BuildTicket) -> int:
        return (
            len(self._executions(ticket))
            + len([report for report in self.store.list_review_reports() if report.ticket_id == ticket.id])
            + len(self.store.list_artifacts_for_ticket(ticket.id))
        )

    def _blocked_reason(
        self,
        ticket: BuildTicket,
        assignment: TicketAssignment | None,
        execution: ExecutionResult | None,
    ) -> str | None:
        if assignment and assignment.blocker:
            return assignment.blocker
        if execution and execution.blocked:
            return execution.block_reason
        if ticket.status is TicketStatus.BLOCKED:
            return ticket.description
        return None

    def _route_decision(self, assignment: TicketAssignment | None) -> dict[str, str | None] | None:
        if assignment is None:
            return None
        route_id = assignment.metadata.get("route_decision_id")
        if not route_id:
            return None
        return {
            "id": str(route_id),
            "path": self._artifact_path(str(route_id)),
            "backend_name": assignment.backend_name,
            "assignment_id": assignment.id,
        }

    def _handoff(
        self,
        ticket: BuildTicket,
        assignment: TicketAssignment | None,
        execution: ExecutionResult | None,
    ) -> dict[str, str | None] | None:
        handoffs = self.store.list_handoffs_for_ticket(ticket.id)
        latest_handoff = sorted(handoffs, key=lambda item: item.created_at)[-1] if handoffs else None
        handoff_id = assignment.metadata.get("handoff_packet_id") if assignment else None
        if latest_handoff is None and handoff_id is None and not execution:
            return None
        effective_handoff_id = str(handoff_id or (latest_handoff.id if latest_handoff else ""))
        return {
            "id": effective_handoff_id,
            "payload_ref": latest_handoff.payload_ref if latest_handoff else None,
            "handoff_file": execution.handoff_file if execution else None,
            "assignment_id": assignment.id if assignment else None,
        }

    def _diff_summary(self, execution: ExecutionResult | None) -> str | None:
        if execution is None:
            return None
        if execution.diff_artifact_id:
            return self._artifact_path(execution.diff_artifact_id)
        return f"{len(execution.changed_files)} changed files"

    def _test_summary(self, execution: ExecutionResult | None) -> str | None:
        if execution is None:
            return None
        if not execution.test_command:
            return None
        return f"{execution.test_command}: exit {execution.test_exit_code}"

    def _review_summary(self, review: ReviewReport | None) -> str | None:
        if review is None:
            return None
        return f"{review.verdict.value}: {len(review.failed_checks)} failed checks, {len(review.warnings)} warnings"

    def _next_issue_links(self, ticket: BuildTicket) -> list[str]:
        return sorted(
            candidate.key
            for candidate in self.store.list_tickets()
            if candidate.metadata.get("generated_from_ticket_key") == ticket.key
            or candidate.metadata.get("source_ticket_key") == ticket.key
            or candidate.metadata.get("parent_ticket_key") == ticket.key
        )
