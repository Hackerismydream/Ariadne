from __future__ import annotations

from ariadne_ltb.application.daemon_control import DaemonControlService
from ariadne_ltb.application.dtos import AgentTaskSnapshotDTO, AgentTaskSnapshotResponse
from ariadne_ltb.models import AssignmentStatus
from ariadne_ltb.storage import AriadneStore


class WorkbenchTaskSnapshotService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def get(self) -> AgentTaskSnapshotResponse:
        daemon = DaemonControlService(self.store).status()
        assignments = self.store.list_assignments()
        active = self._active_assignment()
        snapshot = AgentTaskSnapshotDTO(
            active_assignment=active.id if active else daemon.current_assignment_id,
            current_issue_key=active.ticket_key if active else daemon.current_ticket_key,
            backend=active.backend_name if active else None,
            queued_count=sum(
                1
                for item in assignments
                if item.status in {
                    AssignmentStatus.QUEUED,
                    AssignmentStatus.ROUTED,
                    AssignmentStatus.HANDOFF_READY,
                    AssignmentStatus.AWAITING_USER_APPROVAL,
                    AssignmentStatus.READY_TO_CLAIM,
                }
            ),
            blocked_count=sum(1 for item in assignments if item.status is AssignmentStatus.BLOCKED),
            heartbeat=daemon.heartbeat_at,
            last_event=daemon.last_message or daemon.last_error,
        )
        return AgentTaskSnapshotResponse(snapshot=snapshot)

    def _active_assignment(self):
        active_statuses = {AssignmentStatus.CLAIMED, AssignmentStatus.RUNNING}
        active = [assignment for assignment in self.store.list_assignments() if assignment.status in active_statuses]
        if active:
            return sorted(active, key=lambda item: item.started_at or item.claimed_at or item.created_at)[-1]
        return None
