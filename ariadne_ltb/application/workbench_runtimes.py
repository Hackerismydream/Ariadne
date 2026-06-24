from __future__ import annotations

from ariadne_ltb.application.daemon_control import DaemonControlService
from ariadne_ltb.application.current_version_scope import current_version_mainline_tickets, current_version_target_project_id
from ariadne_ltb.application.dtos import AssignmentListResponse, RuntimeListItemDTO, RuntimeListResponse
from ariadne_ltb.application.mappers import assignment_dto
from ariadne_ltb.application.runtime_status import RuntimeStatusService
from ariadne_ltb.application.work_truth import current_active_assignment
from ariadne_ltb.defaults import OFFLINE_TEST_BACKEND
from ariadne_ltb.models import AssignmentStatus
from ariadne_ltb.storage import AriadneStore


class WorkbenchRuntimesService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def list_runtimes(self) -> RuntimeListResponse:
        daemon = DaemonControlService(self.store).status()
        active = current_active_assignment(self.store, daemon)
        current_ticket_ids = self._current_ticket_ids()
        queue_depth = sum(
            1
            for assignment in self.store.list_assignments()
            if assignment.ticket_id in current_ticket_ids
            and assignment.status in {
                AssignmentStatus.QUEUED,
                AssignmentStatus.ROUTED,
                AssignmentStatus.HANDOFF_READY,
                AssignmentStatus.AWAITING_USER_APPROVAL,
                AssignmentStatus.READY_TO_CLAIM,
            }
        )
        return RuntimeListResponse(
            runtimes=[
                RuntimeListItemDTO(
                    runtime_id=f"local:{capability.backend_name}",
                    backend_name=capability.backend_name,
                    display_name=capability.display_name,
                    daemon_state=daemon.status,
                    available=capability.available,
                    can_assign=capability.can_assign,
                    can_run=capability.can_run,
                    external_execution_enabled=capability.external_execution_enabled,
                    command_template_set=capability.command_template_set,
                    queue_depth=queue_depth,
                    active_assignment=active.id if active else None,
                    disabled_reasons=capability.disabled_reasons,
                )
                for capability in RuntimeStatusService(self.store).snapshot(include_internal=False)
                if capability.backend_name != OFFLINE_TEST_BACKEND
            ]
        )

    def list_assignments(self) -> AssignmentListResponse:
        current_ticket_ids = self._current_ticket_ids()
        return AssignmentListResponse(
            assignments=[
                assignment_dto(assignment)
                for assignment in self.store.list_assignments()
                if assignment.backend_name != OFFLINE_TEST_BACKEND and assignment.ticket_id in current_ticket_ids
            ]
        )

    def _current_ticket_ids(self) -> set[str]:
        target_project_id = current_version_target_project_id(self.store)
        return {
            ticket.id for ticket in current_version_mainline_tickets(self.store, target_project_id)
        }
