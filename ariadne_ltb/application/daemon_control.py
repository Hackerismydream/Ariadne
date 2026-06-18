from __future__ import annotations

import threading
from dataclasses import asdict
from pathlib import Path

from ariadne_ltb.application.dtos import (
    DaemonControlOutput,
    DaemonStartInput,
    DaemonStatusDTO,
    RunAssignmentInput,
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
    ) -> None:
        self.root = root
        self.runtime_id = runtime_id
        self.interval_seconds = interval_seconds
        self.max_iterations = max_iterations
        self.timeout_seconds = timeout_seconds
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
                confirm_execution=False,
                assignment_id=None,
                timeout_seconds=self.timeout_seconds,
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
        handle = _DAEMON_HANDLES.get(self.store.root)
        heartbeat = self._latest_heartbeat(runtime_id)
        open_assignments = self.store.list_open_assignments()
        return DaemonStatusDTO(
            runtime_id=runtime_id,
            status=heartbeat.status.value if heartbeat else "unknown",
            background_running=bool(handle and handle.alive),
            stale=is_stale_heartbeat(heartbeat) if heartbeat else None,
            current_assignment_id=heartbeat.current_assignment_id if heartbeat else None,
            current_ticket_key=heartbeat.current_ticket_key if heartbeat else None,
            current_stage=heartbeat.current_stage if heartbeat else None,
            heartbeat_at=heartbeat.heartbeat_at if heartbeat else None,
            last_event_id=heartbeat.last_event_id if heartbeat else None,
            last_error=heartbeat.last_error if heartbeat else None,
            open_assignment_count=len(open_assignments),
            claimable_assignment_count=sum(
                1 for assignment in open_assignments if assignment.status is AssignmentStatus.QUEUED
            ),
            running_assignment_count=sum(
                1 for assignment in open_assignments if assignment.status is AssignmentStatus.RUNNING
            ),
            blocked_assignment_count=sum(
                1 for assignment in self.store.list_assignments() if assignment.status is AssignmentStatus.BLOCKED
            ),
            last_message=handle.last_message if handle else "",
        )

    def start(self, payload: DaemonStartInput) -> DaemonControlOutput:
        existing = _DAEMON_HANDLES.get(self.store.root)
        if existing and existing.alive:
            return DaemonControlOutput(
                daemon=self.status(existing.runtime_id),
                did_work=False,
                status="already_running",
                message="local daemon loop is already running",
            )
        handle = _DaemonLoopHandle(
            root=self.store.root,
            runtime_id=payload.runtime_id,
            interval_seconds=payload.interval_seconds,
            max_iterations=payload.max_iterations,
            timeout_seconds=payload.timeout_seconds,
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
        return DaemonControlOutput(
            daemon=self.status(runtime_id),
            did_work=False,
            status="stopped",
            message="local daemon loop stopped",
        )

    def run_now(self, assignment_id: str, payload: RunAssignmentInput) -> DaemonControlOutput:
        dispatch = RunAssignmentService(self.store).run(assignment_id, payload)
        result = LocalDaemonWorker(self.store, runtime_id="workbench-local").run_once(
            confirm_execution=False,
            timeout_seconds=payload.timeout_seconds,
            assignment_id=assignment_id,
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

    def _latest_heartbeat(self, runtime_id: str):
        try:
            return self.store.load_worker_heartbeat(runtime_id)
        except FileNotFoundError:
            heartbeats = self.store.list_worker_heartbeats()
            if not heartbeats:
                return None
            return sorted(heartbeats, key=lambda heartbeat: heartbeat.heartbeat_at)[-1]
