from __future__ import annotations

from ariadne_ltb.application.dtos import WorkbenchDTO
from ariadne_ltb.application.mappers import assignment_dto, ticket_summary
from ariadne_ltb.application.runtime_status import RuntimeStatusService
from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.storage import AriadneStore


class WorkbenchProjectionService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def get(self, include_internal_backends: bool = False) -> WorkbenchDTO:
        return WorkbenchDTO(
            tickets=[ticket_summary(self.store, ticket) for ticket in self.store.list_tickets()],
            assignments=[assignment_dto(assignment) for assignment in self.store.list_assignments()],
            runtime_capabilities=RuntimeStatusService(self.store).snapshot(include_internal_backends),
            target_projects=TargetProjectRegistry(self.store).list(),
        )
