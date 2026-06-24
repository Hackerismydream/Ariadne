from __future__ import annotations

from ariadne_ltb.application.daemon_control import DaemonControlService
from ariadne_ltb.application.dtos import AgentTaskSnapshotDTO, AgentTaskSnapshotResponse
from ariadne_ltb.application.work_truth import current_active_assignment, is_claimable_assignment
from ariadne_ltb.models import AssignmentStatus
from ariadne_ltb.storage import AriadneStore


class WorkbenchTaskSnapshotService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def get(self) -> AgentTaskSnapshotResponse:
        daemon = DaemonControlService(self.store).status()
        assignments = self.store.list_assignments()
        active = current_active_assignment(self.store, daemon)
        snapshot = AgentTaskSnapshotDTO(
            active_assignment=active.id if active else None,
            current_issue_key=active.ticket_key if active else None,
            backend=active.backend_name if active else None,
            queued_count=sum(
                1 for item in assignments if is_claimable_assignment(item)
            ),
            blocked_count=sum(1 for item in assignments if item.status is AssignmentStatus.BLOCKED),
            heartbeat=daemon.heartbeat_at,
            last_event=daemon.last_message or daemon.last_error,
        )
        return AgentTaskSnapshotResponse(snapshot=snapshot)
