from __future__ import annotations

import subprocess

from ariadne_ltb.application.confirmation_tokens import ConfirmationTokenService
from ariadne_ltb.application.dtos import RunAssignmentInput, RunAssignmentOutput
from ariadne_ltb.application.idempotency import IdempotencyStore
from ariadne_ltb.application.mappers import assignment_dto
from ariadne_ltb.journal import runtime_event
from ariadne_ltb.models import CommentAuthorType, CommentKind, stable_id
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
        ready_assignment = assignment.mark_ready_to_claim(_readiness_metadata(self.store, assignment, ticket))
        self.store.save_assignment(ready_assignment)
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


def _readiness_metadata(store: AriadneStore, assignment, ticket) -> dict[str, str]:  # noqa: ANN001
    target_project_id = assignment.metadata.get("target_project_id") or ticket.metadata.get("target_project_id")
    target_repo_path = assignment.metadata.get("target_repo_path") or ""
    if target_project_id and not target_repo_path:
        target_repo_path = _target_project_path(store, str(target_project_id))
    expected_git_head = _git_head(target_repo_path) if target_repo_path else "unknown"
    return {
        "target_project_id": str(target_project_id or ""),
        "route_decision_id": str(assignment.metadata.get("route_decision_id") or stable_id("route", assignment.id)),
        "handoff_packet_id": str(assignment.metadata.get("handoff_packet_id") or stable_id("handoff", assignment.id)),
        "permission_profile_id": str(assignment.metadata.get("permission_profile_id") or "local_workbench_default"),
        "confirmation_id": str(assignment.metadata.get("confirmation_id") or stable_id("confirmation", assignment.id)),
        "handoff_hash": str(assignment.metadata.get("handoff_hash") or stable_id("handoff_hash", assignment.id)),
        "target_repo_path": str(target_repo_path),
        "expected_git_head": expected_git_head,
    }


def _git_head(target_repo_path: str) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=target_repo_path,
            check=True,
            text=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def _target_project_path(store: AriadneStore, target_project_id: str) -> str:
    for resource in store.load_project_resources():
        if resource.id == target_project_id:
            return str(resource.resource_ref.get("local_path") or "")
    return ""
