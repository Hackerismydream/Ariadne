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
    InboxActionInput,
    IssueFactoryPreviewInput,
    IssuePatchInput,
    RegisterTargetProjectInput,
    RunAssignmentInput,
)
from ariadne_ltb.application.daemon_control import DaemonControlService
from ariadne_ltb.application.errors import ApplicationError
from ariadne_ltb.application.evidence_projection import EvidenceProjectionService
from ariadne_ltb.application.inbox_actions import InboxActionService
from ariadne_ltb.application.issue_factory import IssueFactoryService
from ariadne_ltb.application.mappers import (
    assignment_dto,
    inbox_item_dto,
    source_artifact_dto,
    source_document_dto,
    source_evidence_dto,
    ticket_summary,
)
from ariadne_ltb.application.project_inputs import build_project_inputs
from ariadne_ltb.application.project_goals import ProjectGoalService
from ariadne_ltb.application.run_assignment import RunAssignmentService
from ariadne_ltb.application.run_events import AssignmentEventCache, RunEventService
from ariadne_ltb.application.runtime_status import RuntimeStatusService
from ariadne_ltb.application.source_analysis import SourceAnalysisService
from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.application.web_sources import WebSourceService
from ariadne_ltb.application.workbench_agents import WorkbenchAgentsService
from ariadne_ltb.application.workbench_inbox import WorkbenchInboxService
from ariadne_ltb.application.workbench_issue_detail import WorkbenchIssueDetailService
from ariadne_ltb.application.workbench_issues import WorkbenchIssuesService
from ariadne_ltb.application.workbench_projects import WorkbenchProjectsService
from ariadne_ltb.application.workbench_projection import WorkbenchProjectionService
from ariadne_ltb.application.workbench_runtimes import WorkbenchRuntimesService
from ariadne_ltb.application.workbench_task_snapshot import WorkbenchTaskSnapshotService
from ariadne_ltb.interfaces.http.dependencies import get_store
from ariadne_ltb.storage import AriadneStore

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "api", "schema_version": "ariadne.health.v1"}


@router.get("/api/workbench")
def get_workbench(
    include_internal_backends: bool = False,
    store: AriadneStore = Depends(get_store),
) -> dict:
    return WorkbenchProjectionService(store).get(include_internal_backends).model_dump(mode="json")


@router.get("/api/issues")
def list_issues(store: AriadneStore = Depends(get_store)) -> dict:
    return WorkbenchIssuesService(store).list().model_dump(mode="json")


@router.get("/api/issues/{issue_id_or_key}")
def get_issue(issue_id_or_key: str, store: AriadneStore = Depends(get_store)) -> dict:
    return WorkbenchIssueDetailService(store).get(issue_id_or_key).model_dump(mode="json")


@router.patch("/api/issues/{issue_id_or_key}")
def patch_issue(
    issue_id_or_key: str,
    payload: IssuePatchInput,
    store: AriadneStore = Depends(get_store),
) -> dict:
    return WorkbenchIssuesService(store).patch(issue_id_or_key, payload).model_dump(mode="json")


@router.post("/api/issues/{issue_id_or_key}/comments")
def create_issue_comment(
    issue_id_or_key: str,
    payload: CreateCommentInput,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: AriadneStore = Depends(get_store),
) -> dict:
    if idempotency_key and not payload.idempotency_key:
        payload = payload.model_copy(update={"idempotency_key": idempotency_key})
    return {
        "comment": WorkbenchIssuesService(store)
        .add_comment(issue_id_or_key, payload)["comment"]
        .model_dump(mode="json")
    }


@router.get("/api/issues/{issue_id_or_key}/timeline")
def issue_timeline(issue_id_or_key: str, store: AriadneStore = Depends(get_store)) -> dict:
    return WorkbenchIssuesService(store).timeline(issue_id_or_key).model_dump(mode="json")


@router.post("/api/issues/{issue_id_or_key}/assign")
def assign_issue(
    issue_id_or_key: str,
    payload: AssignTicketInput,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: AriadneStore = Depends(get_store),
) -> dict:
    if idempotency_key and not payload.idempotency_key:
        payload = payload.model_copy(update={"idempotency_key": idempotency_key})
    return WorkbenchIssuesService(store).assign(issue_id_or_key, payload).model_dump(mode="json")


@router.post("/api/issues/{issue_id_or_key}/rerun")
def rerun_issue(
    issue_id_or_key: str,
    payload: RunAssignmentInput,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: AriadneStore = Depends(get_store),
) -> dict:
    if idempotency_key and not payload.idempotency_key:
        payload = payload.model_copy(update={"idempotency_key": idempotency_key})
    return WorkbenchIssuesService(store).rerun(issue_id_or_key, payload).model_dump(mode="json")


@router.post("/api/issues/{issue_id_or_key}/run-now")
def run_issue_now(
    issue_id_or_key: str,
    payload: RunAssignmentInput,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: AriadneStore = Depends(get_store),
) -> dict:
    if idempotency_key and not payload.idempotency_key:
        payload = payload.model_copy(update={"idempotency_key": idempotency_key})
    return WorkbenchIssuesService(store).run_now(issue_id_or_key, payload).model_dump(mode="json")


@router.get("/api/inbox")
def list_inbox(store: AriadneStore = Depends(get_store)) -> dict:
    return WorkbenchInboxService(store).list().model_dump(mode="json")


@router.get("/api/agent-task-snapshot")
def agent_task_snapshot(store: AriadneStore = Depends(get_store)) -> dict:
    return WorkbenchTaskSnapshotService(store).get().model_dump(mode="json")


@router.get("/api/projects")
def list_projects(store: AriadneStore = Depends(get_store)) -> dict:
    return WorkbenchProjectsService(store).list().model_dump(mode="json")


@router.get("/api/projects/{project_id}")
def get_project(project_id: str, store: AriadneStore = Depends(get_store)) -> dict:
    return WorkbenchProjectsService(store).detail(project_id).model_dump(mode="json")


@router.get("/api/team/agents")
def list_team_agents(store: AriadneStore = Depends(get_store)) -> dict:
    return WorkbenchAgentsService(store).list_agents().model_dump(mode="json")


@router.get("/api/team/build-teams")
def list_build_teams(store: AriadneStore = Depends(get_store)) -> dict:
    return WorkbenchAgentsService(store).list_build_teams().model_dump(mode="json")


@router.get("/api/team/skills")
def list_team_skills(store: AriadneStore = Depends(get_store)) -> dict:
    return WorkbenchAgentsService(store).list_skills().model_dump(mode="json")


@router.get("/api/runs/runtimes")
def list_run_runtimes(store: AriadneStore = Depends(get_store)) -> dict:
    return WorkbenchRuntimesService(store).list_runtimes().model_dump(mode="json")


@router.get("/api/runs/assignments")
def list_run_assignments(store: AriadneStore = Depends(get_store)) -> dict:
    return WorkbenchRuntimesService(store).list_assignments().model_dump(mode="json")


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
    project = TargetProjectRegistry(store).register(
        payload.path,
        payload.label,
        create_if_missing=payload.create_if_missing,
        init_git=payload.init_git,
        test_command=payload.test_command,
        issue_prefix=payload.issue_prefix,
    )
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


@router.get("/api/sources/{source_id}")
def get_source_detail(
    source_id: str,
    store: AriadneStore = Depends(get_store),
) -> dict:
    for detail in build_project_inputs(store):
        if detail.source.id == source_id:
            return {"project_input": detail.model_dump(mode="json")}
    raise ApplicationError("source_not_found", f"Source not found: {source_id}", 404, {"source_id": source_id})


@router.post("/api/sources")
def create_source(
    payload: CreateSourceInput,
    store: AriadneStore = Depends(get_store),
) -> dict:
    service = WebSourceService(store)
    source = service.find_duplicate(payload.path_or_url)
    duplicate = source is not None
    if source is None:
        source = service.create(payload)
    if payload.auto_analyze and str(source.metadata.get("analysis_status") or "pending") != "analyzed":
        SourceAnalysisService(store).analyze_source(source.id)
        source = store.load_source_document(source.id)
    return {
        "source": source_document_dto(store, source).model_dump(mode="json"),
        "duplicate": duplicate,
        "project_input": next(
            (
                detail.model_dump(mode="json")
                for detail in build_project_inputs(store)
                if detail.source.id == source.id
            ),
            None,
        ),
    }


@router.post("/api/sources/{source_id}/analyze")
def analyze_source(
    source_id: str,
    store: AriadneStore = Depends(get_store),
) -> dict:
    result = SourceAnalysisService(store).analyze_source(source_id)
    source = store.load_source_document(source_id)
    return {
        "result": {
            "source_id": result.source_id,
            "status": result.status,
            "artifact_ids": result.artifact_ids,
            "evidence_ids": result.evidence_ids,
            "error": result.error,
        },
        "source": source_document_dto(store, source).model_dump(mode="json"),
        "artifacts": [
            source_artifact_dto(artifact).model_dump(mode="json")
            for artifact in store.list_source_artifacts(source_id)
        ],
        "evidence": [
            source_evidence_dto(evidence).model_dump(mode="json")
            for evidence in store.list_source_evidence(source_id)
        ],
        "project_input": next(
            (
                detail.model_dump(mode="json")
                for detail in build_project_inputs(store)
                if detail.source.id == source_id
            ),
            None,
        ),
    }


@router.post("/api/issue-factory/preview")
def create_issue_factory_preview(
    payload: IssueFactoryPreviewInput,
    store: AriadneStore = Depends(get_store),
) -> dict:
    return {"preview": IssueFactoryService(store).preview(payload).model_dump(mode="json")}


@router.post("/api/issue-factory/{preview_id}/refresh")
def refresh_issue_factory_preview(
    preview_id: str,
    payload: IssueFactoryPreviewInput,
    store: AriadneStore = Depends(get_store),
) -> dict:
    # Refresh is intentionally preview-only. It never applies a stale preview.
    preview = IssueFactoryService(store).preview(payload)
    return {"previous_preview_id": preview_id, "preview": preview.model_dump(mode="json")}


@router.post("/api/issue-factory/{preview_id}/apply")
def apply_issue_factory_preview(
    preview_id: str,
    store: AriadneStore = Depends(get_store),
) -> dict:
    try:
        return IssueFactoryService(store).apply(preview_id).model_dump(mode="json")
    except ValueError as exc:
        if str(exc).startswith("stale_preview"):
            raise ApplicationError(
                "stale_preview",
                "This task-change preview is stale because the project issue set changed. Regenerate task changes and apply the new preview.",
                409,
                {"preview_id": preview_id},
            ) from exc
        raise


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


def _inbox_action_payload(store: AriadneStore, result) -> dict:
    return {
        "inbox_item": inbox_item_dto(store, result.inbox_item).model_dump(mode="json"),
        "action": result.action,
        "message": result.message,
        "ticket": ticket_summary(store, result.ticket).model_dump(mode="json") if result.ticket else None,
        "assignment": assignment_dto(result.assignment).model_dump(mode="json") if result.assignment else None,
        "already_exists": result.already_exists,
    }


@router.post("/api/inbox/{item_id}/repair")
def inbox_create_repair(
    item_id: str,
    payload: InboxActionInput,
    store: AriadneStore = Depends(get_store),
) -> dict:
    result = InboxActionService(store).create_repair_ticket(item_id, priority=payload.priority)
    return _inbox_action_payload(store, result)


@router.post("/api/inbox/{item_id}/rerun")
def inbox_rerun_assignment(
    item_id: str,
    payload: InboxActionInput,
    store: AriadneStore = Depends(get_store),
) -> dict:
    result = InboxActionService(store).rerun_linked_assignment(
        item_id,
        reason=payload.reason,
        force=payload.force,
    )
    return _inbox_action_payload(store, result)


@router.post("/api/inbox/{item_id}/acknowledge")
def inbox_acknowledge(
    item_id: str,
    payload: InboxActionInput,
    store: AriadneStore = Depends(get_store),
) -> dict:
    result = InboxActionService(store).acknowledge(item_id, note=payload.note)
    return _inbox_action_payload(store, result)


@router.post("/api/inbox/{item_id}/resolve")
def inbox_resolve(
    item_id: str,
    payload: InboxActionInput,
    store: AriadneStore = Depends(get_store),
) -> dict:
    result = InboxActionService(store).resolve(item_id, note=payload.note)
    return _inbox_action_payload(store, result)


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
