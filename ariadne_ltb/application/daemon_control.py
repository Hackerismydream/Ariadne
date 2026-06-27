from __future__ import annotations

import threading
from dataclasses import asdict
from pathlib import Path

from ariadne_ltb.application.dtos import (
    DaemonControlOutput,
    DaemonStartInput,
    DaemonStatusDTO,
    QueuePreviewDTO,
    RunAssignmentInput,
    RuntimeScopeDTO,
)
from ariadne_ltb.application.assignment_control import (
    canonicalize_duplicate_runnable_assignments,
    is_claimable_assignment,
)
from ariadne_ltb.application.mappers import assignment_dto
from ariadne_ltb.application.run_assignment import RunAssignmentService
from ariadne_ltb.daemon import LocalDaemonWorker, is_stale_heartbeat
from ariadne_ltb.models import AssignmentStatus
from ariadne_ltb.storage import AriadneStore


class _DaemonLoopHandle:
    def __init__(
        self,
        root: Path,
        runtime_id: str,
        interval_seconds: float,
        max_iterations: int | None,
        timeout_seconds: int | None,
        external_execution_authorized: bool,
        allowed_assignment_id: str | None,
        target_project_id: str | None,
        project_version_id: str | None,
        target_version_label: str | None,
        ticket_id: str | None,
        ticket_key: str | None,
        allowed_backends: list[str],
        block_without_external_authorization: bool,
        scope_mode: str,
    ) -> None:
        self.root = root
        self.runtime_id = runtime_id
        self.interval_seconds = interval_seconds
        self.max_iterations = max_iterations
        self.timeout_seconds = timeout_seconds
        self.external_execution_authorized = external_execution_authorized
        self.allowed_assignment_id = allowed_assignment_id
        self.target_project_id = target_project_id
        self.project_version_id = project_version_id
        self.target_version_label = target_version_label
        self.ticket_id = ticket_id
        self.ticket_key = ticket_key
        self.allowed_backends = allowed_backends
        self.block_without_external_authorization = block_without_external_authorization
        self.scope_mode = scope_mode
        self.stop_event = threading.Event()
        self.last_message = "starting"
        self.thread = threading.Thread(target=self._run, name=f"ariadne-daemon-{runtime_id}", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()

    @property
    def alive(self) -> bool:
        return self.thread.is_alive()

    def _run(self) -> None:
        iterations = 0
        store = AriadneStore(self.root)
        worker = LocalDaemonWorker(store, runtime_id=self.runtime_id)
        while not self.stop_event.is_set():
            result = worker.run_once(
                confirm_execution=self.external_execution_authorized,
                assignment_id=self.allowed_assignment_id,
                target_project_id=self.target_project_id,
                project_version_id=self.project_version_id,
                target_version_label=self.target_version_label,
                ticket_id=self.ticket_id,
                ticket_key=self.ticket_key,
                allowed_backends=self.allowed_backends,
                block_without_external_authorization=self.block_without_external_authorization,
                timeout_seconds=self.timeout_seconds,
                isolate_worktree=False,
            )
            self.last_message = result.message
            iterations += 1
            if self.max_iterations is not None and iterations >= self.max_iterations:
                break
            self.stop_event.wait(self.interval_seconds)
        self.last_message = "stopped"


_DAEMON_HANDLES: dict[Path, _DaemonLoopHandle] = {}


class DaemonControlService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def status(self, runtime_id: str = "workbench-local") -> DaemonStatusDTO:
        canonicalize_duplicate_runnable_assignments(self.store)
        handle = _DAEMON_HANDLES.get(self.store.root)
        heartbeat = self._latest_heartbeat(runtime_id)
        open_assignments = self.store.list_open_assignments()
        stale = is_stale_heartbeat(heartbeat) if heartbeat else None
        background_running = bool(handle and handle.alive and stale is not True)
        external_execution_authorized = bool(background_running and handle and handle.external_execution_authorized)
        scope = RuntimeScopeDTO(
            mode=handle.scope_mode if handle else "paused",
            target_project_id=handle.target_project_id if handle else None,
            project_version_id=handle.project_version_id if handle else None,
            target_version_label=handle.target_version_label if handle else None,
            ticket_id=handle.ticket_id if handle else None,
            ticket_key=handle.ticket_key if handle else None,
            assignment_id=handle.allowed_assignment_id if handle else None,
            allowed_backends=handle.allowed_backends if handle else [],
        )
        return DaemonStatusDTO(
            runtime_id=runtime_id,
            status=heartbeat.status.value if heartbeat else "unknown",
            background_running=background_running,
            external_execution_authorized=external_execution_authorized,
            stale=stale,
            current_assignment_id=heartbeat.current_assignment_id if heartbeat else None,
            current_ticket_key=heartbeat.current_ticket_key if heartbeat else None,
            current_stage=heartbeat.current_stage if heartbeat else None,
            heartbeat_at=heartbeat.heartbeat_at if heartbeat else None,
            last_event_id=heartbeat.last_event_id if heartbeat else None,
            last_error=heartbeat.last_error if heartbeat else None,
            open_assignment_count=len(open_assignments),
            claimable_assignment_count=sum(
                1 for assignment in open_assignments if assignment.status is AssignmentStatus.READY_TO_CLAIM
            ),
            running_assignment_count=sum(
                1 for assignment in open_assignments if assignment.status is AssignmentStatus.RUNNING
            ),
            blocked_assignment_count=sum(
                1 for assignment in self.store.list_assignments() if assignment.status is AssignmentStatus.BLOCKED
            ),
            last_message=handle.last_message if handle else "",
            scope=scope,
            queue_preview=self._queue_preview(scope),
        )

    def start(self, payload: DaemonStartInput) -> DaemonControlOutput:
        canonicalize_duplicate_runnable_assignments(self.store)
        if self._is_broad_claim(payload):
            claimable = [
                assignment
                for assignment in self.store.list_open_assignments()
                if is_claimable_assignment(assignment)
            ]
            if len(claimable) > 1:
                return DaemonControlOutput(
                    daemon=self.status(payload.runtime_id),
                    did_work=False,
                    status="broad_claim_blocked",
                    message=(
                        "daemon start needs an assignment, project, or backend scope when multiple "
                        "claimable assignments exist"
                    ),
                )
        existing = _DAEMON_HANDLES.get(self.store.root)
        heartbeat = self._latest_heartbeat(payload.runtime_id)
        heartbeat_stale = is_stale_heartbeat(heartbeat) if heartbeat else False
        daemon_scope_changed = bool(
            existing
            and (
                existing.runtime_id != payload.runtime_id
                or existing.allowed_assignment_id != payload.allowed_assignment_id
                or existing.target_project_id != payload.target_project_id
                or existing.project_version_id != payload.project_version_id
                or existing.target_version_label != payload.target_version_label
                or existing.ticket_id != payload.ticket_id
                or existing.ticket_key != payload.ticket_key
                or existing.allowed_backends != payload.allowed_backends
                or existing.scope_mode != payload.scope_mode
            )
        )
        if existing and existing.alive and not heartbeat_stale and not daemon_scope_changed:
            return DaemonControlOutput(
                daemon=self.status(existing.runtime_id),
                did_work=False,
                status="already_running",
                message="local daemon loop is already running",
            )
        if existing and existing.alive:
            existing.stop()
            existing.thread.join(timeout=2)
            _DAEMON_HANDLES.pop(self.store.root, None)
        handle = _DaemonLoopHandle(
            root=self.store.root,
            runtime_id=payload.runtime_id,
            interval_seconds=payload.interval_seconds,
            max_iterations=payload.max_iterations,
            timeout_seconds=payload.timeout_seconds,
            external_execution_authorized=payload.external_execution_authorized,
            allowed_assignment_id=payload.allowed_assignment_id,
            target_project_id=payload.target_project_id,
            project_version_id=payload.project_version_id,
            target_version_label=payload.target_version_label,
            ticket_id=payload.ticket_id,
            ticket_key=payload.ticket_key,
            allowed_backends=payload.allowed_backends,
            block_without_external_authorization=not payload.external_execution_authorized
            and bool(payload.allowed_assignment_id),
            scope_mode=payload.scope_mode,
        )
        _DAEMON_HANDLES[self.store.root] = handle
        handle.start()
        return DaemonControlOutput(
            daemon=self.status(payload.runtime_id),
            did_work=False,
            status="started",
            message="local daemon loop started",
        )

    def stop(self, runtime_id: str = "workbench-local") -> DaemonControlOutput:
        handle = _DAEMON_HANDLES.get(self.store.root)
        if handle:
            handle.stop()
            handle.thread.join(timeout=2)
            _DAEMON_HANDLES.pop(self.store.root, None)
        return DaemonControlOutput(
            daemon=self.status(runtime_id),
            did_work=False,
            status="stopped",
            message="local daemon loop stopped",
        )

    def run_now(self, assignment_id: str, payload: RunAssignmentInput) -> DaemonControlOutput:
        dispatch = RunAssignmentService(self.store).run(assignment_id, payload)
        handle = _DAEMON_HANDLES.get(self.store.root)
        external_execution_authorized = bool(handle and handle.alive and handle.external_execution_authorized)
        requested_assignment = self.store.load_assignment(assignment_id)
        result = LocalDaemonWorker(self.store, runtime_id="workbench-local").run_once(
            confirm_execution=external_execution_authorized,
            timeout_seconds=payload.timeout_seconds,
            assignment_id=assignment_id,
            target_project_id=requested_assignment.metadata.get("target_project_id"),
            project_version_id=requested_assignment.metadata.get("project_version_id"),
            target_version_label=requested_assignment.metadata.get("target_version_label"),
            ticket_id=requested_assignment.metadata.get("issue_ticket_id") or requested_assignment.ticket_id,
            ticket_key=requested_assignment.metadata.get("issue_ticket_key") or requested_assignment.ticket_key,
            allowed_backends=[requested_assignment.backend_name] if requested_assignment.backend_name else None,
            isolate_worktree=False,
        )
        assignment = self.store.load_assignment(assignment_id)
        return DaemonControlOutput(
            daemon=self.status("workbench-local"),
            did_work=result.did_work,
            assignment=assignment_dto(assignment),
            status=result.status,
            message=result.message or dispatch.message,
            ticket_run_result=asdict(result.ticket_run_result) if result.ticket_run_result else None,
        )

    def _is_broad_claim(self, payload: DaemonStartInput) -> bool:
        return (
            not payload.allowed_assignment_id
            and not payload.target_project_id
            and not payload.project_version_id
            and not payload.target_version_label
            and not payload.ticket_id
            and not payload.ticket_key
            and not payload.allowed_backends
            and payload.scope_mode != "paused"
        )

    def _latest_heartbeat(self, runtime_id: str):
        try:
            return self.store.load_worker_heartbeat(runtime_id)
        except FileNotFoundError:
            heartbeats = self.store.list_worker_heartbeats()
            if not heartbeats:
                return None
            return sorted(heartbeats, key=lambda heartbeat: heartbeat.heartbeat_at)[-1]

    def _queue_preview(self, scope: RuntimeScopeDTO) -> QueuePreviewDTO:
        assignments = self.store.list_open_assignments()
        current = None
        if scope.assignment_id:
            try:
                current = assignment_dto(self.store.load_assignment(scope.assignment_id))
            except FileNotFoundError:
                current = None
        same_ticket = []
        same_project = []
        if current:
            same_ticket = [
                assignment_dto(item)
                for item in assignments
                if item.ticket_id == current.ticket_id and item.status is AssignmentStatus.READY_TO_CLAIM
            ][:10]
        if scope.target_project_id:
            same_project = [
                assignment_dto(item)
                for item in assignments
                if item.metadata.get("target_project_id") == scope.target_project_id
                and (
                    not scope.project_version_id
                    or item.metadata.get("project_version_id") == scope.project_version_id
                )
                and (
                    not scope.target_version_label
                    or item.metadata.get("target_version_label") == scope.target_version_label
                )
                and item.status is AssignmentStatus.READY_TO_CLAIM
            ][:20]
        scoped_ids = {item.id for item in same_ticket + same_project}
        if current:
            scoped_ids.add(current.id)
        out_of_scope = sum(1 for item in assignments if item.id not in scoped_ids)
        return QueuePreviewDTO(
            current=current,
            same_ticket_ready=same_ticket,
            same_project_ready=same_project,
            out_of_scope_ready_count=out_of_scope,
        )
