from __future__ import annotations

from dataclasses import asdict

from ariadne_ltb.application.confirmation_tokens import ConfirmationTokenService
from ariadne_ltb.application.dtos import RunAssignmentInput, RunAssignmentOutput
from ariadne_ltb.application.idempotency import IdempotencyStore
from ariadne_ltb.application.mappers import assignment_dto
from ariadne_ltb.daemon import LocalDaemonWorker
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
        result = LocalDaemonWorker(self.store, runtime_id="web").run_once(
            confirm_execution=True,
            agent_runtime=assignment.agent_runtime,
            backlog_planner=assignment.backlog_planner_name,
            timeout_seconds=payload.timeout_seconds,
            assignment_id=assignment_id,
        )
        assignment = self.store.load_assignment(assignment_id)
        run_result = asdict(result.ticket_run_result) if result.ticket_run_result else None
        self.idempotency.set(
            payload.idempotency_key,
            {
                "assignment_id": assignment.id,
                "did_work": result.did_work,
                "status": result.status,
                "message": result.message,
                "ticket_run_result": run_result,
            },
            "run_assignment",
        )
        return RunAssignmentOutput(
            assignment=assignment_dto(assignment),
            did_work=result.did_work,
            status=result.status,
            message=result.message,
            ticket_run_result=run_result,
        )
