from __future__ import annotations

from ariadne_ltb.application.assignment_readiness import prepare_assignment_for_claim
from ariadne_ltb.application.confirmation_tokens import ConfirmationTokenService
from ariadne_ltb.application.dtos import RunAssignmentInput, RunAssignmentOutput
from ariadne_ltb.application.idempotency import IdempotencyStore
from ariadne_ltb.application.mappers import assignment_dto
from ariadne_ltb.journal import runtime_event
from ariadne_ltb.models import CommentAuthorType, CommentKind
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
        ready_assignment = prepare_assignment_for_claim(self.store, assignment, ticket)
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
