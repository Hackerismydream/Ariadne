from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Header

from ariadne_ltb.application.assign_ticket import AssignTicketService
from ariadne_ltb.application.comments import CommentService
from ariadne_ltb.application.dtos import (
    AssignTicketInput,
    CreateCommentInput,
    RegisterTargetProjectInput,
    RunAssignmentOutput,
    RunAssignmentInput,
)
from ariadne_ltb.application.confirmation_tokens import ConfirmationTokenService
from ariadne_ltb.application.evidence_projection import EvidenceProjectionService
from ariadne_ltb.application.mappers import assignment_dto
from ariadne_ltb.application.run_assignment import RunAssignmentService
from ariadne_ltb.application.run_events import RunEventService
from ariadne_ltb.application.runtime_status import RuntimeStatusService
from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.application.workbench_projection import WorkbenchProjectionService
from ariadne_ltb.interfaces.http.dependencies import get_store
from ariadne_ltb.storage import AriadneStore

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/workbench")
def get_workbench(
    include_internal_backends: bool = False,
    store: AriadneStore = Depends(get_store),
) -> dict:
    return WorkbenchProjectionService(store).get(include_internal_backends).model_dump(mode="json")


@router.get("/api/runtime/status")
def runtime_status(
    include_internal: bool = False,
    store: AriadneStore = Depends(get_store),
) -> dict:
    capabilities = RuntimeStatusService(store).snapshot(include_internal)
    return {"capabilities": [capability.model_dump(mode="json") for capability in capabilities]}


@router.get("/api/target-projects")
def list_target_projects(store: AriadneStore = Depends(get_store)) -> dict:
    return {"target_projects": [item.model_dump(mode="json") for item in TargetProjectRegistry(store).list()]}


@router.post("/api/target-projects")
def register_target_project(
    payload: RegisterTargetProjectInput,
    store: AriadneStore = Depends(get_store),
) -> dict:
    project = TargetProjectRegistry(store).register(payload.path, payload.label)
    return {"target_project": project.model_dump(mode="json")}


@router.post("/api/tickets/{ticket_id_or_key}/assign")
def assign_ticket(
    ticket_id_or_key: str,
    payload: AssignTicketInput,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: AriadneStore = Depends(get_store),
) -> dict:
    if idempotency_key and not payload.idempotency_key:
        payload = payload.model_copy(update={"idempotency_key": idempotency_key})
    return AssignTicketService(store).assign(ticket_id_or_key, payload, source="http").model_dump(mode="json")


@router.post("/api/assignments/{assignment_id}/run")
def run_assignment(
    assignment_id: str,
    payload: RunAssignmentInput,
    background_tasks: BackgroundTasks,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: AriadneStore = Depends(get_store),
) -> dict:
    if idempotency_key and not payload.idempotency_key:
        payload = payload.model_copy(update={"idempotency_key": idempotency_key})
    assignment = store.load_assignment(assignment_id)
    ConfirmationTokenService(store).verify(assignment, payload.confirmation_token)
    background_tasks.add_task(
        RunAssignmentService(store).run,
        assignment_id,
        payload.model_copy(update={"idempotency_key": None}),
    )
    return RunAssignmentOutput(
        assignment=assignment_dto(assignment),
        did_work=False,
        status=assignment.status.value,
        message="run accepted; watch assignment events for progress",
    ).model_dump(mode="json")


@router.get("/api/assignments/{assignment_id}/events")
def assignment_events(
    assignment_id: str,
    since: str | None = None,
    store: AriadneStore = Depends(get_store),
) -> dict:
    return RunEventService(store).assignment_events(assignment_id, since=since).model_dump(mode="json")


@router.get("/api/tickets/{ticket_id_or_key}/timeline")
def ticket_timeline(ticket_id_or_key: str, store: AriadneStore = Depends(get_store)) -> dict:
    return CommentService(store).timeline(ticket_id_or_key).model_dump(mode="json")


@router.get("/api/evidence")
def evidence_projection(store: AriadneStore = Depends(get_store)) -> dict:
    return EvidenceProjectionService(store).snapshot().model_dump(mode="json")


@router.post("/api/tickets/{ticket_id_or_key}/comments")
def create_comment(
    ticket_id_or_key: str,
    payload: CreateCommentInput,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: AriadneStore = Depends(get_store),
) -> dict:
    if idempotency_key and not payload.idempotency_key:
        payload = payload.model_copy(update={"idempotency_key": idempotency_key})
    return {"comment": CommentService(store).add_human_comment(ticket_id_or_key, payload).model_dump(mode="json")}


@router.get("/api/runs/{run_id}/messages")
def run_messages(run_id: str, since: int = 0, store: AriadneStore = Depends(get_store)) -> dict:
    return {"messages": RunEventService(store).messages(run_id, since)}
