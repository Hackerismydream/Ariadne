from __future__ import annotations

from typing import Literal

from ariadne_ltb.application.assignment_routing import prepare_direct_agent_assignment
from ariadne_ltb.application.confirmation_tokens import ConfirmationTokenService
from ariadne_ltb.application.dtos import AssignTicketInput, AssignTicketOutput
from ariadne_ltb.application.errors import NotFoundError, ValidationAppError
from ariadne_ltb.application.idempotency import IdempotencyStore
from ariadne_ltb.application.mappers import assignment_dto, ticket_summary
from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.defaults import OFFLINE_TEST_BACKEND
from ariadne_ltb.domain.runtime_policy import (
    resolve_runtime_profile,
    runtime_profile_values,
    validate_backend_for_source,
)
from ariadne_ltb.models import TicketAssignment, TicketStatus
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.team import route_ticket_to_build_team


class AssignTicketService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store
        self.idempotency = IdempotencyStore(store)

    def assign(
        self,
        ticket_id_or_key: str,
        payload: AssignTicketInput,
        source: Literal["http", "cli", "test"] = "http",
    ) -> AssignTicketOutput:
        replay = self.idempotency.get(payload.idempotency_key, "assign_ticket")
        if replay:
            assignment = self.store.load_assignment(replay["assignment_id"])
            return AssignTicketOutput(
                ticket=ticket_summary(self.store, assignment.ticket_id),
                assignment=assignment_dto(assignment),
                confirmation_token=None,
                route_decision_artifact_path=replay.get("route_decision_artifact_path"),
                idempotent_replay=True,
            )
        ticket = self.store.resolve_ticket(ticket_id_or_key)
        try:
            validate_backend_for_source(source, payload.backend_name)
            effective_profile = resolve_runtime_profile(payload.runtime_profile, payload.backend_name)
            runtime_values = runtime_profile_values(effective_profile)
        except ValueError as exc:
            raise ValidationAppError(str(exc)) from exc
        target_repo_path = TargetProjectRegistry(self.store).resolve_path(payload.target_project_id)
        if payload.assignee_kind == "build_team":
            try:
                team = self.store.resolve_build_team(payload.assignee_id)
            except FileNotFoundError as exc:
                raise NotFoundError(str(exc)) from exc
            routed = route_ticket_to_build_team(
                self.store,
                ticket,
                team,
                backend_name=payload.backend_name,
                planner_name=runtime_values.planner_name,
                agent_runtime=runtime_values.agent_runtime,
                backlog_planner_name=runtime_values.backlog_planner_name,
                target_repo_path=target_repo_path,
                target_project_id=payload.target_project_id,
            )
            assignment = self._with_target_metadata(
                routed.assignment,
                payload.target_project_id,
                target_repo_path,
            )
            route_path = routed.route_artifact.path
        elif payload.assignee_kind == "agent":
            try:
                agent = self.store.resolve_agent_profile(payload.assignee_id)
            except FileNotFoundError as exc:
                raise NotFoundError(str(exc)) from exc
            assignment = self.store.create_assignment(
                ticket,
                agent,
                backend_name=payload.backend_name,
                planner_name=runtime_values.planner_name,
                agent_runtime=runtime_values.agent_runtime,
                backlog_planner_name=runtime_values.backlog_planner_name,
            )
            assignment = self._with_target_metadata(assignment, payload.target_project_id, target_repo_path)
            assignment = prepare_direct_agent_assignment(
                self.store,
                ticket=ticket,
                assignment=assignment,
                agent=agent,
                target_project_id=payload.target_project_id,
                target_repo_path=target_repo_path,
            )
            self.store.save_ticket(
                self.store.load_ticket(ticket.id).with_status(
                    TicketStatus.READY_FOR_EXECUTION
                    if (assignment.backend_name or agent.backend_name) == OFFLINE_TEST_BACKEND
                    else TicketStatus.WAITING_APPROVAL,
                    "Ariadne",
                    f"Assigned to {agent.name}.",
                )
            )
            route_path = None
        else:
            raise ValidationAppError("assignee_kind must be agent or build_team")
        confirmation_token = ConfirmationTokenService(self.store).issue_for_assignment(assignment)
        self.idempotency.set(
            payload.idempotency_key,
            {
                "assignment_id": assignment.id,
                "route_decision_artifact_path": route_path,
            },
            "assign_ticket",
        )
        return AssignTicketOutput(
            ticket=ticket_summary(self.store, assignment.ticket_id),
            assignment=assignment_dto(assignment),
            confirmation_token=confirmation_token,
            route_decision_artifact_path=route_path,
        )

    def _with_target_metadata(
        self,
        assignment: TicketAssignment,
        target_project_id: str,
        target_repo_path: str,
    ) -> TicketAssignment:
        updated = assignment.model_copy(
            deep=True,
            update={
                "metadata": assignment.metadata
                | {"target_project_id": target_project_id, "target_repo_path": target_repo_path}
            },
        )
        self.store.save_assignment(updated)
        ticket = self.store.load_ticket(updated.ticket_id).model_copy(
            deep=True,
            update={
                "metadata": self.store.load_ticket(updated.ticket_id).metadata
                | {
                    "latest_assignment_id": updated.id,
                    "target_project_id": target_project_id,
                    "target_repo_path": target_repo_path,
                }
            },
        )
        self.store.save_ticket(ticket)
        return updated
