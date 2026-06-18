from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from ariadne_ltb.daemon import DaemonRunResult, LocalDaemonWorker
from ariadne_ltb.inbox import (
    InboxRecoveryBatchResult,
    InboxRepairDispatchResult,
    dispatch_repair_tickets,
    recover_inbox_items,
    refresh_inbox,
)
from ariadne_ltb.models import AgentProfile, InboxItem, stable_id, utc_now
from ariadne_ltb.storage import AriadneStore


@dataclass(frozen=True)
class SupervisorRunOnceResult:
    refreshed_inbox_items: list[InboxItem]
    recovery: InboxRecoveryBatchResult | None
    dispatch: InboxRepairDispatchResult | None
    daemon: DaemonRunResult | None


@dataclass(frozen=True)
class SupervisorLoopCycle:
    index: int
    result: SupervisorRunOnceResult
    action_count: int
    status: str


@dataclass(frozen=True)
class SupervisorLoopResult:
    cycles: list[SupervisorLoopCycle]
    stop_reason: str
    report_path: Path


def supervisor_run_once(
    store: AriadneStore,
    agent: AgentProfile,
    backend_name: str | None = None,
    planner_name: str | None = None,
    agent_runtime: str | None = None,
    backlog_planner_name: str | None = None,
    limit: int | None = None,
    recover: bool = True,
    dispatch: bool = True,
    run_daemon: bool = False,
    runtime_id: str = "local",
    confirm_execution: bool = False,
    timeout_seconds: int | None = None,
) -> SupervisorRunOnceResult:
    """Run one local supervisor pass without crossing safety gates by default."""

    refreshed = refresh_inbox(store)
    recovery = (
        recover_inbox_items(
            store,
            refresh=False,
            limit=limit,
        )
        if recover
        else None
    )
    dispatch_result = (
        dispatch_repair_tickets(
            store,
            agent,
            backend_name=backend_name,
            planner_name=planner_name,
            agent_runtime=agent_runtime,
            backlog_planner_name=backlog_planner_name,
            limit=limit,
        )
        if dispatch
        else None
    )
    daemon_result = (
        LocalDaemonWorker(store, runtime_id=runtime_id).run_once(
            confirm_execution=confirm_execution,
            agent_runtime=agent_runtime,
            backlog_planner=backlog_planner_name,
            timeout_seconds=timeout_seconds,
        )
        if run_daemon
        else None
    )
    return SupervisorRunOnceResult(
        refreshed_inbox_items=refreshed,
        recovery=recovery,
        dispatch=dispatch_result,
        daemon=daemon_result,
    )


def supervisor_loop(
    store: AriadneStore,
    agent: AgentProfile,
    backend_name: str | None = None,
    planner_name: str | None = None,
    agent_runtime: str | None = None,
    backlog_planner_name: str | None = None,
    limit: int | None = None,
    recover: bool = True,
    dispatch: bool = True,
    run_daemon: bool = False,
    runtime_id: str = "local",
    confirm_execution: bool = False,
    timeout_seconds: int | None = None,
    max_cycles: int = 3,
    interval_seconds: float = 0.0,
    stop_after_idle_cycles: int = 1,
) -> SupervisorLoopResult:
    """Run a bounded supervisor loop and persist a compact JSON report."""

    if max_cycles < 1:
        raise ValueError("max_cycles must be positive")
    if interval_seconds < 0:
        raise ValueError("interval_seconds must be non-negative")
    if stop_after_idle_cycles < 0:
        raise ValueError("stop_after_idle_cycles must be non-negative")

    cycles: list[SupervisorLoopCycle] = []
    idle_cycles = 0
    stop_reason = "max_cycles"
    started_at = utc_now()
    report_id = stable_id("supervisor_loop", started_at, agent.id, runtime_id)
    report_path = store.base / "supervisor" / f"{report_id}.json"

    for index in range(1, max_cycles + 1):
        result = supervisor_run_once(
            store,
            agent,
            backend_name=backend_name,
            planner_name=planner_name,
            agent_runtime=agent_runtime,
            backlog_planner_name=backlog_planner_name,
            limit=limit,
            recover=recover,
            dispatch=dispatch,
            run_daemon=run_daemon,
            runtime_id=runtime_id,
            confirm_execution=confirm_execution,
            timeout_seconds=timeout_seconds,
        )
        action_count = supervisor_action_count(result)
        status = "idle" if action_count == 0 else "worked"
        cycles.append(
            SupervisorLoopCycle(
                index=index,
                result=result,
                action_count=action_count,
                status=status,
            )
        )

        if result.daemon and result.daemon.status in {"blocked", "failed"}:
            stop_reason = f"daemon_{result.daemon.status}"
            break
        if action_count == 0:
            idle_cycles += 1
        else:
            idle_cycles = 0
        if stop_after_idle_cycles and idle_cycles >= stop_after_idle_cycles:
            stop_reason = "idle"
            break
        if index < max_cycles and interval_seconds:
            time.sleep(interval_seconds)

    _write_loop_report(
        report_path,
        {
            "id": report_id,
            "started_at": started_at,
            "finished_at": utc_now(),
            "agent_id": agent.id,
            "agent_name": agent.name,
            "backend_name": backend_name,
            "planner_name": planner_name,
            "agent_runtime": agent_runtime,
            "backlog_planner_name": backlog_planner_name,
            "runtime_id": runtime_id,
            "run_daemon": run_daemon,
            "confirm_execution": confirm_execution,
            "max_cycles": max_cycles,
            "interval_seconds": interval_seconds,
            "stop_after_idle_cycles": stop_after_idle_cycles,
            "stop_reason": stop_reason,
            "cycle_count": len(cycles),
            "cycles": [
                {
                    "index": cycle.index,
                    "status": cycle.status,
                    "action_count": cycle.action_count,
                    "result": summarize_run_once(cycle.result),
                }
                for cycle in cycles
            ],
        },
    )
    return SupervisorLoopResult(cycles=cycles, stop_reason=stop_reason, report_path=report_path)


def summarize_run_once(result: SupervisorRunOnceResult) -> dict:
    return {
        "inbox_count": len(result.refreshed_inbox_items),
        "recovery": None
        if result.recovery is None
        else {
            "recovered_count": len(result.recovery.recovered),
            "created_ticket_count": result.recovery.created_ticket_count,
            "existing_ticket_count": result.recovery.existing_ticket_count,
            "preview_count": result.recovery.preview_count,
            "skipped_count": len(result.recovery.skipped),
            "tickets": [
                item.ticket.key if item.ticket else item.preview.id if item.preview else item.inbox_item.id
                for item in result.recovery.recovered
            ],
        },
        "dispatch": None
        if result.dispatch is None
        else {
            "assigned_count": len(result.dispatch.assignments),
            "skipped_count": len(result.dispatch.skipped),
            "assignments": [
                {
                    "assignment_id": assignment.id,
                    "ticket_key": assignment.ticket_key,
                    "agent_id": assignment.agent_id,
                    "backend": assignment.backend_name,
                    "planner": assignment.planner_name,
                    "agent_runtime": assignment.agent_runtime,
                    "backlog_planner": assignment.backlog_planner_name,
                }
                for assignment in result.dispatch.assignments
            ],
            "skipped": [
                {"ticket_key": item.ticket.key, "reason": item.reason}
                for item in result.dispatch.skipped
            ],
        },
        "daemon": None
        if result.daemon is None
        else {
            "did_work": result.daemon.did_work,
            "assignment_id": result.daemon.assignment_id,
            "ticket_key": result.daemon.ticket_key,
            "status": result.daemon.status,
            "message": result.daemon.message,
        },
    }


def supervisor_action_count(result: SupervisorRunOnceResult) -> int:
    recovery_count = result.recovery.created_ticket_count if result.recovery else 0
    dispatch_count = len(result.dispatch.assignments) if result.dispatch else 0
    daemon_count = 1 if result.daemon and result.daemon.did_work else 0
    return recovery_count + dispatch_count + daemon_count


def _write_loop_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
