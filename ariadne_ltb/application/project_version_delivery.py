from __future__ import annotations

from collections import Counter

from ariadne_ltb.application.dtos import (
    DeliveryGateDTO,
    DeliveryItemDTO,
    LatestRealRunDTO,
    ProjectVersionDeliveryDTO,
)
from ariadne_ltb.application.current_version_scope import current_version_mainline_tickets
from ariadne_ltb.application.project_goals import ProjectGoalService
from ariadne_ltb.application.work_truth import reduce_work_truth
from ariadne_ltb.models import BuildTicket, ExecutionResult, ProjectResource, ReviewReport, utc_now
from ariadne_ltb.storage import AriadneStore


REAL_BACKENDS = {"codex", "claude", "claude-code"}


def build_current_version_delivery(store: AriadneStore) -> ProjectVersionDeliveryDTO | None:
    tickets = store.list_tickets()
    goals = ProjectGoalService(store).list()
    resources = store.load_project_resources()
    if not tickets and not goals and not resources:
        return None
    goal = _active_goal(goals)
    target_project_id = _active_target_project_id(goal, tickets, resources)
    target = _target_resource(resources, target_project_id)
    delivery_tickets = current_version_mainline_tickets(store, target_project_id) or [
        ticket for ticket in tickets if _belongs_to_target(ticket, target_project_id)
    ] or tickets
    items = [_delivery_item(store, ticket) for ticket in sorted(delivery_tickets, key=lambda item: item.key)]
    latest_real_run = _latest_real_run(store, items)
    gates = _gates(store, items, latest_real_run)
    status = _status(gates, latest_real_run, items)
    blockers = [gate.detail for gate in gates if gate.status == "blocked" and gate.detail]
    return ProjectVersionDeliveryDTO(
        id=f"delivery:{target_project_id or 'default'}",
        version_label=_version_label(goal, target),
        status=status,
        goal_id=goal.id if goal else None,
        target_project_id=target_project_id,
        target_project_label=target.label if target else None,
        current_state=_current_state(status, items, latest_real_run),
        target_state=goal.target_state if goal and goal.target_state else "目标项目形成一个可运行版本。",
        summary=_summary(status, items, latest_real_run),
        generated_at=utc_now(),
        progress_counts=dict(Counter(item.evidence_status for item in items)),
        gates=gates,
        delivery_items=items,
        latest_real_run=latest_real_run,
        blockers=blockers,
        next_actions=_next_actions(status, gates),
        evidence_refs=[item.execution_result_id for item in items if item.execution_result_id],
    )


def _active_goal(goals):  # noqa: ANN001
    if not goals:
        return None
    return max(enumerate(goals), key=lambda item: (item[1].created_at, -item[0]))[1]


def _active_target_project_id(goal, tickets: list[BuildTicket], resources: list[ProjectResource]) -> str | None:  # noqa: ANN001
    if goal and goal.target_project_id:
        return goal.target_project_id
    ids = [str(ticket.metadata.get("target_project_id")) for ticket in tickets if ticket.metadata.get("target_project_id")]
    if ids:
        return Counter(ids).most_common(1)[0][0]
    return resources[-1].id if resources else None


def _target_resource(resources: list[ProjectResource], target_project_id: str | None) -> ProjectResource | None:
    if target_project_id is None:
        return resources[-1] if resources else None
    return next((resource for resource in resources if resource.id == target_project_id), None)


def _belongs_to_target(ticket: BuildTicket, target_project_id: str | None) -> bool:
    if target_project_id is None:
        return True
    return ticket.metadata.get("target_project_id") == target_project_id


def _delivery_item(store: AriadneStore, ticket: BuildTicket) -> DeliveryItemDTO:
    assignment = store.find_latest_assignment_for_ticket(ticket.id)
    execution = _latest_execution(store, ticket)
    review = _review(store, ticket)
    truth = reduce_work_truth(assignment=assignment, execution=execution, review=review)
    memory_path = str(store.memory_dir / "tickets" / f"{ticket.id}.json")
    return DeliveryItemDTO(
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        title=ticket.title,
        status=ticket.status.value,
        priority=ticket.priority,
        target_project_id=ticket.metadata.get("target_project_id"),
        assignment_id=assignment.id if assignment else None,
        assignment_status=assignment.status.value if assignment else None,
        backend_name=execution.backend_name if execution else assignment.backend_name if assignment else None,
        route_decision_id=assignment.metadata.get("route_decision_id") if assignment else None,
        handoff_packet_id=assignment.metadata.get("handoff_packet_id") if assignment else None,
        build_context_id=ticket.metadata.get("build_context_id") or (assignment.metadata.get("build_context_id") if assignment else None),
        execution_result_id=execution.id if execution else ticket.metadata.get("execution_result_id"),
        dry_run=execution.dry_run if execution else None,
        blocked=execution.blocked if execution else None,
        exit_code=execution.exit_code if execution else None,
        test_command=execution.test_command if execution else None,
        test_exit_code=execution.test_exit_code if execution else None,
        review_verdict=review.verdict.value if review else None,
        memory_path=memory_path if (store.memory_dir / "tickets" / f"{ticket.id}.json").exists() else ticket.metadata.get("memory_path"),
        feishu_plan_path=ticket.metadata.get("feishu_plan_path"),
        next_tickets_path=ticket.metadata.get("next_tickets_path"),
        changed_files=list(truth.agent_changed_files),
        preflight_dirty_files=list(truth.preflight_dirty_files),
        acceptance_criteria=[str(item) for item in ticket.metadata.get("acceptance_criteria", [])],
        evidence_status=_evidence_status(assignment, execution, review),
        terminal_verdict=truth.terminal_verdict,
    )


def _latest_execution(store: AriadneStore, ticket: BuildTicket) -> ExecutionResult | None:
    result_id = ticket.metadata.get("execution_result_id")
    if result_id:
        try:
            return store.load_execution_result(result_id)
        except FileNotFoundError:
            pass
    results = [result for result in store.list_execution_results() if result.ticket_id == ticket.id]
    return sorted(results, key=lambda item: item.ended_at)[-1] if results else None


def _review(store: AriadneStore, ticket: BuildTicket) -> ReviewReport | None:
    review_id = ticket.metadata.get("review_report_id")
    if review_id:
        try:
            return store.load_review_report(review_id)
        except FileNotFoundError:
            pass
    reports = [report for report in store.list_review_reports() if report.ticket_id == ticket.id]
    return sorted(reports, key=lambda item: item.created_at)[-1] if reports else None


def _evidence_status(assignment, execution: ExecutionResult | None, review: ReviewReport | None) -> str:  # noqa: ANN001
    truth = reduce_work_truth(assignment=assignment, execution=execution, review=review)
    if truth.terminal_verdict == "blocked_before_execution":
        return "blocked_before_execution"
    if truth.terminal_verdict == "executed_failed":
        return "executed_failed"
    if truth.terminal_verdict == "review_blocked":
        return "review_blocked"
    if truth.terminal_verdict == "succeeded":
        if execution and execution.backend_name in REAL_BACKENDS and not execution.dry_run:
            return "real_pass"
        return "offline_pass"
    if execution is None:
        return "missing"
    return "partial"


def _latest_real_run(store: AriadneStore, items: list[DeliveryItemDTO]) -> LatestRealRunDTO | None:
    execution_ids = {item.execution_result_id for item in items if item.execution_result_id}
    executions = [
        result
        for result in store.list_execution_results()
        if result.id in execution_ids and result.backend_name in REAL_BACKENDS and not result.dry_run
    ]
    if not executions:
        return None
    execution = sorted(executions, key=lambda item: item.ended_at)[-1]
    ticket = store.load_ticket(execution.ticket_id)
    review = _review(store, ticket)
    truth = reduce_work_truth(execution=execution, review=review)
    return LatestRealRunDTO(
        ticket_key=ticket.key,
        assignment_id=execution.assignment_id or ticket.metadata.get("latest_assignment_id"),
        backend_name=execution.backend_name,
        execution_result_id=execution.id,
        exit_code=execution.exit_code,
        test_exit_code=execution.test_exit_code,
        review_verdict=review.verdict.value if review else None,
        dry_run=execution.dry_run,
        blocked=execution.blocked,
        terminal_verdict=truth.terminal_verdict,
        changed_files=list(truth.agent_changed_files),
        preflight_dirty_files=list(truth.preflight_dirty_files),
        handoff_file=execution.handoff_file,
        diff_artifact_path=_artifact_path(store, execution.diff_artifact_id),
        execution_log_artifact_path=_artifact_path(store, execution.execution_log_artifact_id),
        memory_path=ticket.metadata.get("memory_path"),
        next_tickets_path=ticket.metadata.get("next_tickets_path"),
    )


def _artifact_path(store: AriadneStore, artifact_id: str | None) -> str | None:
    if not artifact_id:
        return None
    try:
        return store.load_artifact(artifact_id).path
    except FileNotFoundError:
        return None


def _gates(store: AriadneStore, items: list[DeliveryItemDTO], latest: LatestRealRunDTO | None) -> list[DeliveryGateDTO]:
    source_ready = any(store.list_source_artifacts())
    preview_applied = any(preview.applied_at for preview in store.list_backlog_previews())
    assignment_ready = any(item.assignment_id for item in items)
    assignment_blocked = next(
        (item for item in items if item.evidence_status == "blocked_before_execution" and item.assignment_status in {"blocked", "failed"}),
        None,
    )
    real_closed = bool(
        latest
        and latest.terminal_verdict == "succeeded"
    )
    real_execution_detail = "真实 Codex/Claude 执行证据缺失。"
    if latest and latest.terminal_verdict != "succeeded":
        real_execution_detail = f"真实执行未闭环：{latest.terminal_verdict}。"
    return [
        DeliveryGateDTO(
            id="sources",
            label="外部输入理解",
            status="done" if source_ready else "blocked",
            detail="" if source_ready else "还没有可用于任务工厂的 source artifact。",
        ),
        DeliveryGateDTO(
            id="issue_delta",
            label="任务变更确认",
            status="done" if preview_applied or items else "blocked",
            detail="" if preview_applied or items else "还没有已应用的任务变更。",
        ),
        DeliveryGateDTO(
            id="assignment",
            label="任务分配",
            status="blocked" if assignment_blocked else "done" if assignment_ready else "blocked",
            detail=(
                f"{assignment_blocked.ticket_key} assignment {assignment_blocked.assignment_status}。"
                if assignment_blocked
                else "" if assignment_ready else "还没有 assignment。"
            ),
            ref_id=assignment_blocked.assignment_id if assignment_blocked else None,
        ),
        DeliveryGateDTO(
            id="real_execution",
            label="真实 Codex/Claude 执行",
            status="done" if real_closed else "blocked",
            detail="" if real_closed else real_execution_detail,
            ref_id=latest.execution_result_id if latest else None,
        ),
        DeliveryGateDTO(
            id="review",
            label="Review",
            status="done" if real_closed else "blocked",
            detail="" if real_closed else "缺少通过 review 的真实执行。",
            ref_id=latest.execution_result_id if latest else None,
        ),
    ]


def _status(gates: list[DeliveryGateDTO], latest: LatestRealRunDTO | None, items: list[DeliveryItemDTO]) -> str:
    if latest and not latest.blocked and latest.exit_code == 0 and latest.test_exit_code in {None, 0} and latest.review_verdict == "pass":
        return "real_closed"
    if any(item.evidence_status in {"blocked_before_execution", "executed_failed", "review_blocked", "blocked"} for item in items):
        return "blocked"
    if any(gate.status == "blocked" for gate in gates):
        return "in_progress"
    return "ready_for_review"


def _current_state(status: str, items: list[DeliveryItemDTO], latest: LatestRealRunDTO | None) -> str:
    if status == "real_closed" and latest:
        return f"{latest.ticket_key} 已由 {latest.backend_name} 完成真实执行，测试和 review 通过。"
    if not items:
        return "还没有目标项目任务。"
    return f"当前有 {len(items)} 个交付任务，状态为 {status}。"


def _target_state(goal) -> str:  # noqa: ANN001
    return goal.target_state if goal and goal.target_state else "目标项目推进到一个可运行版本。"


def _summary(status: str, items: list[DeliveryItemDTO], latest: LatestRealRunDTO | None) -> str:
    if status == "real_closed" and latest:
        return f"真实闭环证据来自 {latest.backend_name} execution {latest.execution_result_id}。"
    return f"当前版本尚未闭环；{len(items)} 个任务正在形成交付证据。"


def _next_actions(status: str, gates: list[DeliveryGateDTO]) -> list[str]:
    if status == "real_closed":
        return ["查看目标仓库 diff/tests/review/memory 证据", "继续处理 next tickets"]
    blocked = next((gate for gate in gates if gate.status == "blocked"), None)
    if blocked:
        return [f"补齐：{blocked.label}"]
    return ["选择一个主线任务并启动 scoped daemon"]


def _version_label(goal, target: ProjectResource | None) -> str:  # noqa: ANN001
    if goal and goal.title:
        return goal.title
    if target:
        label = target.resource_ref.get("target_version") or target.resource_ref.get("version") or "v0.1"
        return f"{target.label} {label}"
    return "当前版本"
