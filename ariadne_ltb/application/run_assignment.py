from __future__ import annotations

from ariadne_ltb.application.confirmation_tokens import ConfirmationTokenService
from ariadne_ltb.application.dtos import RunAssignmentInput, RunAssignmentOutput
from ariadne_ltb.application.errors import ValidationAppError
from ariadne_ltb.application.idempotency import IdempotencyStore
from ariadne_ltb.application.mappers import assignment_dto
from ariadne_ltb.journal import runtime_event
from ariadne_ltb.models import AssignmentStatus, CommentAuthorType, CommentKind
from ariadne_ltb.storage import AriadneStore


class RunAssignmentService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store
        self.idempotency = IdempotencyStore(store)

    def run(self, assignment_id: str, payload: RunAssignmentInput) -> RunAssignmentOutput:
        replay = self.idempotency.get(payload.idempotency_key, "run_assignment")
        if replay:
            assignment = self.store.load_assignment(replay["assignment_id"])
            return RunAssignmentOutput(
                assignment=assignment_dto(assignment),
                did_work=bool(replay.get("did_work")),
                status=str(replay.get("status", assignment.status.value)),
                message=str(replay.get("message", "")),
                ticket_run_result=replay.get("ticket_run_result"),
                idempotent_replay=True,
            )
        assignment = self.store.load_assignment(assignment_id)
        ConfirmationTokenService(self.store).verify(assignment, payload.confirmation_token)
        ticket = self.store.load_ticket(assignment.ticket_id)
        if assignment.status is AssignmentStatus.READY_TO_CLAIM:
            ready_assignment = assignment
        elif assignment.metadata.get("route_decision_id") and assignment.metadata.get("handoff_packet_id"):
            ready_assignment = assignment.mark_ready_to_claim(
                {
                    "route_decision_id": str(assignment.metadata["route_decision_id"]),
                    "handoff_packet_id": str(assignment.metadata["handoff_packet_id"]),
                    "target_project_id": str(
                        assignment.metadata.get("target_project_id") or ticket.metadata.get("target_project_id") or ""
                    ),
                    "target_repo_path": str(assignment.metadata.get("target_repo_path") or ""),
                    "permission_profile_id": str(
                        assignment.metadata.get("permission_profile_id") or "local_workbench_default"
                    ),
                    "runtime_authorization_id": str(
                        assignment.metadata.get("runtime_authorization_id")
                        or assignment.metadata.get("confirmation_id")
                        or ""
                    ),
                    "handoff_hash": str(assignment.metadata.get("handoff_hash") or ""),
                    "expected_git_head": str(assignment.metadata.get("expected_git_head") or "unknown"),
                }
            )
            self.store.save_assignment(ready_assignment)
        else:
            raise ValidationAppError(
                "assignment_not_ready_for_run",
                {
                    "missing": [
                        key
                        for key in ["route_decision_id", "handoff_packet_id"]
                        if not assignment.metadata.get(key)
                    ]
                },
            )
        self.store.add_comment(
            ticket,
            CommentAuthorType.SYSTEM,
            "Ariadne",
            CommentKind.PROGRESS,
            f"Run requested from Workbench for {ticket.key}; waiting for a local daemon runtime to claim it.",
            payload_ref=ready_assignment.id,
            thread_id=ready_assignment.id,
        )
        event = runtime_event(
            ticket,
            "control-plane",
            "dispatch",
            "requested",
            "Ariadne",
            assignment_id=ready_assignment.id,
            payload_ref=ready_assignment.id,
            metadata={
                "timeout_seconds": payload.timeout_seconds,
                "execution_owner": "daemon-runtime",
                "assignment_status": ready_assignment.status.value,
            },
        )
        self.store.append_runtime_event(event)
        message = "run dispatched; start or keep `ari daemon start` running to claim the assignment"
        self.idempotency.set(
            payload.idempotency_key,
            {
                "assignment_id": ready_assignment.id,
                "did_work": False,
                "status": ready_assignment.status.value,
                "message": message,
                "ticket_run_result": None,
            },
            "run_assignment",
        )
        return RunAssignmentOutput(
            assignment=assignment_dto(ready_assignment),
            did_work=False,
            status=ready_assignment.status.value,
            message=message,
            ticket_run_result=None,
        )
