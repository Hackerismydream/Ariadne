from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Header, WebSocket, WebSocketDisconnect

from ariadne_ltb.application.assign_ticket import AssignTicketService
from ariadne_ltb.application.comments import CommentService
from ariadne_ltb.application.dtos import (
    AssignTicketInput,
    CreateCommentInput,
    CreateProjectGoalInput,
    CreateSourceInput,
    DaemonStartInput,
    IssueFactoryPreviewInput,
    RegisterTargetProjectInput,
    RunAssignmentInput,
)
from ariadne_ltb.application.daemon_control import DaemonControlService
from ariadne_ltb.application.evidence_projection import EvidenceProjectionService
from ariadne_ltb.application.issue_factory import IssueFactoryService
from ariadne_ltb.application.mappers import source_document_dto
from ariadne_ltb.application.project_goals import ProjectGoalService
from ariadne_ltb.application.run_assignment import RunAssignmentService
from ariadne_ltb.application.run_events import AssignmentEventCache, RunEventService
from ariadne_ltb.application.runtime_status import RuntimeStatusService
from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.application.web_sources import WebSourceService
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


@router.get("/api/daemon/status")
def daemon_status(store: AriadneStore = Depends(get_store)) -> dict:
    return DaemonControlService(store).status().model_dump(mode="json")


@router.post("/api/daemon/start")
def daemon_start(
    payload: DaemonStartInput,
    store: AriadneStore = Depends(get_store),
) -> dict:
    return DaemonControlService(store).start(payload).model_dump(mode="json")


@router.post("/api/daemon/stop")
def daemon_stop(store: AriadneStore = Depends(get_store)) -> dict:
    return DaemonControlService(store).stop().model_dump(mode="json")


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


@router.get("/api/goals")
def list_goals(store: AriadneStore = Depends(get_store)) -> dict:
    return {"goals": [goal.model_dump(mode="json") for goal in ProjectGoalService(store).list()]}


@router.post("/api/goals")
def create_goal(
    payload: CreateProjectGoalInput,
    store: AriadneStore = Depends(get_store),
) -> dict:
    return {"goal": ProjectGoalService(store).create(payload).model_dump(mode="json")}


@router.get("/api/sources")
def list_sources(store: AriadneStore = Depends(get_store)) -> dict:
    return {"sources": [source_document_dto(store, source).model_dump(mode="json") for source in store.list_source_documents()]}


@router.post("/api/sources")
def create_source(
    payload: CreateSourceInput,
    store: AriadneStore = Depends(get_store),
) -> dict:
    source = WebSourceService(store).create(payload)
    return {"source": source_document_dto(store, source).model_dump(mode="json")}


@router.post("/api/issue-factory/preview")
def create_issue_factory_preview(
    payload: IssueFactoryPreviewInput,
    store: AriadneStore = Depends(get_store),
) -> dict:
    return {"preview": IssueFactoryService(store).preview(payload).model_dump(mode="json")}


@router.post("/api/issue-factory/{preview_id}/apply")
def apply_issue_factory_preview(
    preview_id: str,
    store: AriadneStore = Depends(get_store),
) -> dict:
    return IssueFactoryService(store).apply(preview_id).model_dump(mode="json")


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
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: AriadneStore = Depends(get_store),
) -> dict:
    if idempotency_key and not payload.idempotency_key:
        payload = payload.model_copy(update={"idempotency_key": idempotency_key})
    return RunAssignmentService(store).run(assignment_id, payload).model_dump(mode="json")


@router.post("/api/assignments/{assignment_id}/run-now")
def run_assignment_now(
    assignment_id: str,
    payload: RunAssignmentInput,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: AriadneStore = Depends(get_store),
) -> dict:
    if idempotency_key and not payload.idempotency_key:
        payload = payload.model_copy(update={"idempotency_key": idempotency_key})
    return DaemonControlService(store).run_now(assignment_id, payload).model_dump(mode="json")


@router.get("/api/assignments/{assignment_id}/events")
def assignment_events(
    assignment_id: str,
    since: str | None = None,
    store: AriadneStore = Depends(get_store),
) -> dict:
    return RunEventService(store).assignment_events(assignment_id, since=since).model_dump(mode="json")


@router.websocket("/ws/assignments/{assignment_id}")
async def assignment_event_stream(
    websocket: WebSocket,
    assignment_id: str,
) -> None:
    await websocket.accept()
    store = AriadneStore(websocket.app.state.root)
    cache = AssignmentEventCache()
    service = RunEventService(store, cache=cache)
    cursor = websocket.query_params.get("since")
    try:
        batch = service.assignment_event_stream_batch(assignment_id, since=cursor)
        await websocket.send_json(batch.model_dump(mode="json"))
        cursor = batch.cursor
        while True:
            await asyncio.sleep(1)
            batch = service.assignment_event_stream_batch(assignment_id, since=cursor)
            if batch.events:
                await websocket.send_json(batch.model_dump(mode="json"))
                cursor = batch.cursor
            else:
                heartbeat = service.heartbeat(assignment_id, since=cursor)
                await websocket.send_json(heartbeat.model_dump(mode="json"))
    except WebSocketDisconnect:
        return


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
