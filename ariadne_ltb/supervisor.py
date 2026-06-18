from __future__ import annotations

from dataclasses import dataclass

from ariadne_ltb.daemon import DaemonRunResult, LocalDaemonWorker
from ariadne_ltb.inbox import (
    InboxRecoveryBatchResult,
    InboxRepairDispatchResult,
    dispatch_repair_tickets,
    recover_inbox_items,
    refresh_inbox,
)
from ariadne_ltb.models import AgentProfile, InboxItem
from ariadne_ltb.storage import AriadneStore


@dataclass(frozen=True)
class SupervisorRunOnceResult:
    refreshed_inbox_items: list[InboxItem]
    recovery: InboxRecoveryBatchResult | None
    dispatch: InboxRepairDispatchResult | None
    daemon: DaemonRunResult | None


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
