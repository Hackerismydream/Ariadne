from __future__ import annotations

from ariadne_ltb.application.dtos import AgentActivityDTO, AgentWorkflowStepDTO, ArtifactRefDTO
from ariadne_ltb.models import Artifact, BuildTicket, RuntimeEvent
from ariadne_ltb.storage import AriadneStore


STEP_DEFS = [
    ("knowledge", "Knowledge Agent", "knowledge", "Issue Factory"),
    ("repo_understanding", "Repo Understanding Agent", "repo_understanding", "Issue Factory"),
    ("issue_factory", "Issue Factory", "planning", "Build Lead"),
    ("build_lead", "Build Lead", "routing", "Handoff Agent"),
    ("handoff", "Handoff Agent", "handoff", "Runtime Agent"),
    ("runtime", "Runtime / Daemon", "runtime", "Implementer"),
    ("implementer", "Implementer", "execution", "Reviewer"),
    ("reviewer", "Reviewer", "review", "Memory Agent"),
    ("memory", "Memory Agent", "memory", "Build Lead"),
]


def build_agent_workflows(store: AriadneStore) -> tuple[list[AgentWorkflowStepDTO], list[AgentActivityDTO]]:
    tickets = store.list_tickets()
    activities = _activities(store)
    steps: list[AgentWorkflowStepDTO] = []
    for ticket in tickets:
        ticket_activities = [item for item in activities if item.ticket_id == ticket.id]
        for index, (step_kind, agent_name, agent_role, next_agent) in enumerate(STEP_DEFS, start=1):
            output_refs = _output_refs(store, ticket, step_kind)
            latest = _latest_activity(ticket_activities, step_kind)
            status = _step_status(output_refs, latest)
            assignment = store.find_latest_assignment_for_ticket(ticket.id)
            steps.append(
                AgentWorkflowStepDTO(
                    id=f"{ticket.id}:{step_kind}",
                    ticket_id=ticket.id,
                    ticket_key=ticket.key,
                    sequence=index,
                    agent_name=agent_name,
                    agent_role=agent_role,
                    step_kind=step_kind,
                    status=status,
                    input_refs=_input_refs(store, ticket, step_kind),
                    output_refs=output_refs,
                    assignment_id=assignment.id if assignment and step_kind in {"handoff", "runtime", "implementer"} else None,
                    run_id=latest.run_id if latest else None,
                    handoff_id=output_refs[0].id if output_refs and step_kind == "handoff" else None,
                    next_agent=next_agent,
                    next_action=_next_action(step_kind, status),
                    latest_activity=latest,
                    blocked_reason=assignment.blocker if assignment and assignment.blocker and step_kind in {"runtime", "implementer"} else None,
                )
            )
    return steps, activities


def _activities(store: AriadneStore) -> list[AgentActivityDTO]:
    result: list[AgentActivityDTO] = []
    for event in store.list_runtime_events():
        result.append(_event_activity(event))
    for run in store.list_runs():
        result.append(
            AgentActivityDTO(
                id=f"run:{run.id}",
                ticket_id=run.ticket_id,
                ticket_key=_ticket_key(store, run.ticket_id),
                assignment_id=str(run.metadata.get("assignment_id") or "") or None,
                run_id=run.id,
                agent_name=run.agent_name,
                stage=str(run.metadata.get("stage") or run.agent_role),
                event_type=run.status.value,
                summary=run.output_summary or run.input_summary,
                timestamp=run.ended_at or run.started_at or "",
                ref_id=run.id,
            )
        )
    return sorted(result, key=lambda item: item.timestamp, reverse=True)[:200]


def _event_activity(event: RuntimeEvent) -> AgentActivityDTO:
    return AgentActivityDTO(
        id=f"event:{event.id}",
        ticket_id=event.ticket_id,
        ticket_key=event.ticket_key,
        assignment_id=event.assignment_id,
        run_id=event.run_id,
        agent_name=event.actor,
        stage=event.stage,
        event_type=event.event_type,
        summary=f"{event.stage}: {event.event_type}",
        timestamp=event.timestamp,
        ref_id=event.payload_ref,
    )


def _ticket_key(store: AriadneStore, ticket_id: str) -> str | None:
    try:
        return store.load_ticket(ticket_id).key
    except FileNotFoundError:
        return None


def _latest_activity(activities: list[AgentActivityDTO], step_kind: str) -> AgentActivityDTO | None:
    terms = {
        "knowledge": {"source", "knowledge"},
        "repo_understanding": {"repo", "codebase", "source"},
        "issue_factory": {"backlog", "issue", "planning"},
        "build_lead": {"route", "build_lead", "routing"},
        "handoff": {"handoff"},
        "runtime": {"claim", "runtime", "daemon"},
        "implementer": {"execution"},
        "reviewer": {"review"},
        "memory": {"memory", "feishu", "next"},
    }[step_kind]
    for activity in activities:
        haystack = f"{activity.stage} {activity.event_type} {activity.agent_name}".lower()
        if any(term in haystack for term in terms):
            return activity
    return None


def _input_refs(store: AriadneStore, ticket: BuildTicket, step_kind: str) -> list[ArtifactRefDTO]:
    if step_kind in {"knowledge", "repo_understanding", "issue_factory"}:
        refs: list[ArtifactRefDTO] = []
        for source_id in ticket.metadata.get("source_document_ids", [])[:5]:
            refs.append(ArtifactRefDTO(id=str(source_id), artifact_type="source_document", summary="外部输入"))
        return refs
    if ticket.build_packet_id:
        return [ArtifactRefDTO(id=ticket.build_packet_id, artifact_type="build_packet", summary="Build Packet")]
    return []


def _output_refs(store: AriadneStore, ticket: BuildTicket, step_kind: str) -> list[ArtifactRefDTO]:
    refs: list[ArtifactRefDTO] = []
    if step_kind in {"knowledge", "repo_understanding"}:
        for artifact in store.list_source_artifacts():
            if artifact.id in ticket.metadata.get("source_artifact_ids", []):
                refs.append(
                    ArtifactRefDTO(
                        id=artifact.id,
                        artifact_type=artifact.artifact_type,
                        path=artifact.payload_path,
                        summary=artifact.artifact_type,
                        created_at=str(artifact.created_at),
                    )
                )
    elif step_kind == "issue_factory":
        for preview in store.list_backlog_previews():
            if any(op.ticket_id == ticket.id for op in preview.operations):
                refs.append(ArtifactRefDTO(id=preview.id, artifact_type="backlog_preview", summary=preview.rationale, created_at=preview.created_at))
    elif step_kind == "build_lead":
        route_id = ticket.metadata.get("route_decision_id")
        if route_id:
            refs.append(ArtifactRefDTO(id=str(route_id), artifact_type="route_decision", summary="Route decision"))
    elif step_kind == "handoff":
        refs.extend(_artifact_refs(store.list_handoffs_for_ticket(ticket.id), "handoff"))
    elif step_kind == "implementer":
        execution_id = ticket.metadata.get("execution_result_id")
        if execution_id:
            refs.append(ArtifactRefDTO(id=str(execution_id), artifact_type="execution_result", summary="Execution result"))
    elif step_kind == "reviewer":
        review_id = ticket.metadata.get("review_report_id")
        if review_id:
            refs.append(ArtifactRefDTO(id=str(review_id), artifact_type="review_report", summary="Review report"))
    elif step_kind == "memory":
        for key in ("memory_path", "feishu_plan_path", "next_tickets_path"):
            if ticket.metadata.get(key):
                refs.append(ArtifactRefDTO(id=f"{ticket.id}:{key}", artifact_type=key, path=str(ticket.metadata[key]), summary=key))
    if not refs:
        refs.extend(_ticket_artifact_refs(store, ticket, step_kind))
    return refs


def _artifact_refs(items: object, artifact_type: str) -> list[ArtifactRefDTO]:
    refs: list[ArtifactRefDTO] = []
    for item in items:  # type: ignore[union-attr]
        refs.append(
            ArtifactRefDTO(
                id=item.id,
                artifact_type=artifact_type,
                summary=getattr(item, "summary", "") or artifact_type,
                created_at=getattr(item, "created_at", None),
            )
        )
    return refs


def _ticket_artifact_refs(store: AriadneStore, ticket: BuildTicket, step_kind: str) -> list[ArtifactRefDTO]:
    result: list[ArtifactRefDTO] = []
    for artifact in store.list_artifacts_for_ticket(ticket.id):
        if _artifact_matches_step(artifact, step_kind):
            result.append(
                ArtifactRefDTO(
                    id=artifact.id,
                    artifact_type=artifact.artifact_type.value,
                    path=artifact.path,
                    summary=artifact.summary,
                    created_at=artifact.created_at,
                    metadata=artifact.metadata,
                )
            )
    return result


def _artifact_matches_step(artifact: Artifact, step_kind: str) -> bool:
    value = artifact.artifact_type.value.lower()
    return step_kind in value or (
        step_kind == "implementer" and ("execution" in value or "diff" in value)
    ) or (
        step_kind == "memory" and ("memory" in value or "next" in value or "feishu" in value)
    )


def _step_status(output_refs: list[ArtifactRefDTO], latest: AgentActivityDTO | None) -> str:
    if output_refs:
        return "done"
    if latest:
        if latest.event_type in {"failed", "blocked"}:
            return "blocked"
        return "running"
    return "waiting_for_evidence"


def _next_action(step_kind: str, status: str) -> str:
    if status == "done":
        return "查看输出证据"
    if status == "blocked":
        return "打开 Inbox 恢复动作"
    return {
        "knowledge": "添加或分析输入",
        "issue_factory": "生成任务建议",
        "handoff": "分配任务生成 handoff",
        "runtime": "启动 scoped daemon",
        "implementer": "运行 Codex/Claude",
        "reviewer": "等待 review",
        "memory": "写入记忆和 next tickets",
    }.get(step_kind, "等待上一步证据")
