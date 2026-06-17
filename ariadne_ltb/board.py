from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from ariadne_ltb.local_safety import list_locks
from ariadne_ltb.models import ArtifactType, BuildTicket, TicketStatus, WorkerHeartbeat
from ariadne_ltb.runtime import collect_runtime_capabilities
from ariadne_ltb.storage import AriadneStore


def export_board(store: AriadneStore) -> Path:
    store.board_dir.mkdir(parents=True, exist_ok=True)
    board_path = store.board_dir / "index.md"
    html_path = store.board_dir / "index.html"
    tickets = store.list_tickets()
    sections: list[str] = [
        "# Ariadne v1.0 Workbench",
        "",
        "Static local board export for Ariadne's local Agent teammate workbench.",
        "",
        "## Loop Trace",
        "",
        "`learning input -> build decision -> coding execution -> review -> memory`",
        "",
        "Source -> Ticket -> Packet -> Handoff -> Backend -> Diff -> Tests -> Review -> Memory -> Feishu Plan -> Next Tickets",
        "",
    ]
    sections.extend(_workbench_summary_sections(store, tickets))
    sources = store.list_source_documents()
    if sources:
        sections.extend(["## Source Inputs", ""])
        for source in sources:
            sections.append(f"- `{source.source_type.value}` {source.title} - `{source.path_or_url}`")
        sections.append("")
    by_status: dict[TicketStatus, list[BuildTicket]] = defaultdict(list)
    for ticket in tickets:
        by_status[ticket.status].append(ticket)

    sections.append("## Tickets by Status")
    sections.append("")
    for status in TicketStatus:
        status_tickets = by_status.get(status, [])
        if not status_tickets:
            continue
        sections.append(f"### {status.value}")
        sections.append("")
        for ticket in status_tickets:
            sections.append(f"- `{ticket.key}` {ticket.title} (`{ticket.id}`)")
        sections.append("")

    for ticket in tickets:
        sections.extend(_ticket_section(store, ticket))

    markdown = "\n".join(sections).rstrip() + "\n"
    board_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(_html_from_markdown(markdown), encoding="utf-8")
    return board_path


def _workbench_summary_sections(store: AriadneStore, tickets: list[BuildTicket]) -> list[str]:
    assignments = store.list_assignments()
    open_assignments = store.list_open_assignments()
    events = store.list_runtime_events()
    heartbeats = store.list_worker_heartbeats()
    capabilities = store.load_runtime_capabilities() or collect_runtime_capabilities()
    backlog_updates = store.list_backlog_updates()
    executed = [ticket for ticket in tickets if ticket.metadata.get("execution_result_id")]
    next_ticket_paths = [
        ticket.metadata.get("next_tickets_path")
        for ticket in tickets
        if ticket.metadata.get("next_tickets_path")
    ]
    lines = [
        "## System Summary",
        "",
        f"- Tickets: `{len(tickets)}`",
        f"- Assignments: `{len(assignments)}`",
        f"- Open assignments: `{len(open_assignments)}`",
        f"- Runtime events: `{len(events)}`",
        f"- Executed tickets: `{len(executed)}`",
        "",
        "## Agent Queue",
        "",
    ]
    if assignments:
        for assignment in assignments[-10:]:
            lines.append(
                f"- `{assignment.id}` `{assignment.ticket_key}` -> `{assignment.agent_id}` "
                f"status=`{assignment.status.value}` attempt=`{assignment.attempt}`"
            )
    else:
        lines.append("No assignments yet.")
    lines.extend(["", "## Active Assignments", ""])
    if open_assignments:
        for assignment in open_assignments:
            lines.append(
                f"- `{assignment.id}` `{assignment.ticket_key}` `{assignment.status.value}` "
                f"backend=`{assignment.backend_name or ''}`"
            )
    else:
        lines.append("No active assignments.")
    lines.extend(["", "## Daemon / Runtime", ""])
    if heartbeats:
        for heartbeat in heartbeats:
            lines.append(
                f"- `{heartbeat.runtime_id}` status=`{heartbeat.status.value}` "
                f"stage=`{heartbeat.current_stage or ''}` stale=`{str(_is_stale_heartbeat(heartbeat)).lower()}`"
            )
    else:
        lines.append("No daemon heartbeat yet.")
    lines.extend(["", "## Agent Comments", ""])
    recent_comments = []
    for ticket in tickets:
        recent_comments.extend(store.list_comments(ticket.id)[-3:])
    if recent_comments:
        for comment in recent_comments[-10:]:
            lines.append(f"- `{comment.ticket_key}` `{comment.kind.value}` {comment.author}: {comment.body}")
    else:
        lines.append("No comments yet.")
    lines.extend(["", "## Recent Journal Events", ""])
    if events:
        for event in events[-10:]:
            lines.append(
                f"- `{event.timestamp}` `{event.ticket_key or ''}` "
                f"`{event.stage}:{event.event_type}` {event.actor}"
            )
    else:
        lines.append("No journal events yet.")
    lines.extend(["", "## Executed Tickets", ""])
    if executed:
        for ticket in executed:
            lines.append(f"- `{ticket.key}` {ticket.title}")
    else:
        lines.append("No executed tickets yet.")
    lines.extend(["", "## Next Tickets", ""])
    if next_ticket_paths:
        for path in next_ticket_paths:
            lines.append(f"- `{path}`")
    else:
        lines.append("No next-ticket artifacts yet.")
    lines.extend(["", "## Ticket Backlog Updates", ""])
    if backlog_updates:
        for update in backlog_updates[-10:]:
            lines.append(
                f"- `{update.id}` `{update.trigger_type.value}` Created "
                f"`{len(update.created_ticket_ids)}` Updated `{len(update.updated_ticket_ids)}` "
                f"Superseded `{len(update.superseded_ticket_ids)}` - {update.rationale}"
            )
            if update.evidence_refs:
                lines.append(f"  - Evidence: `{', '.join(update.evidence_refs)}`")
    else:
        lines.append("No ticket backlog updates yet.")
    lines.extend(["", "## Backend Capability", ""])
    for capability in capabilities:
        lines.append(
            f"- `{capability.backend_name}` available=`{str(capability.available).lower()}` "
            f"external=`{str(capability.external_execution_enabled).lower()}`"
        )
    lines.extend(["", "## Safety Gates", ""])
    lines.append(
        "- External execution: "
        f"`{'enabled' if os.environ.get('ARIADNE_ENABLE_EXTERNAL_EXECUTION') == '1' else 'disabled'}`"
    )
    lines.append(
        "- Feishu write: "
        f"`{'enabled' if os.environ.get('FEISHU_ENABLE_WRITE') == '1' else 'disabled'}`"
    )
    lines.extend(["", "## Codex Gate Status", ""])
    codex = next((item for item in capabilities if item.backend_name == "codex"), None)
    if codex:
        lines.append(f"- Command path: `{codex.command_path or 'missing'}`")
        lines.append(f"- Template set: `{str(codex.command_template_set).lower()}`")
        lines.append(f"- Confirm required: `{str(codex.confirm_execution_required).lower()}`")
    else:
        lines.append("Codex capability snapshot missing.")
    lines.append("")
    return lines


def _ticket_section(store: AriadneStore, ticket: BuildTicket) -> list[str]:
    lines = [
        f"## {ticket.key} - {ticket.title}",
        "",
        f"- Ticket ID: `{ticket.id}`",
        f"- Status: `{ticket.status.value}`",
        f"- Owner: `{ticket.owner_agent}`",
        f"- Source: `{ticket.source_ref}`",
        f"- Priority: `{ticket.priority}`",
        "",
    ]
    source_id = ticket.metadata.get("source_document_id")
    if source_id:
        source = store.load_source_document(source_id)
        lines.extend(
            [
                "### Source",
                "",
                f"- Type: `{source.source_type.value}`",
                f"- Title: {source.title}",
                f"- Path: `{source.path_or_url}`",
                "",
            ]
        )
    artifacts = [store.load_artifact(artifact_id) for artifact_id in ticket.artifact_ids]
    assignment = store.find_latest_assignment_for_ticket(ticket.id)
    lines.extend(["## Agent Assignment", ""])
    if assignment:
        lines.extend(
            [
                f"- Assigned agent: `{assignment.agent_name}` (`{assignment.agent_id}`)",
                f"- Assignment status: `{assignment.status.value}`",
                f"- Backend: `{assignment.backend_name or ''}`",
                f"- Claimed by runtime: `{assignment.claimed_by_runtime_id or ''}`",
                f"- Created: `{assignment.created_at}`",
                f"- Claimed: `{assignment.claimed_at or ''}`",
                f"- Ended: `{assignment.ended_at or ''}`",
                "",
            ]
        )
    else:
        lines.extend(["No assignment yet.", ""])

    assignment_chain = store.list_assignments_for_ticket(ticket.id)
    lines.extend(["### Assignment Retry Chain", ""])
    if assignment_chain:
        lines.extend(
            [
                "| Assignment | Status | Attempt | Parent | Failure reason | Retry reason | Created | Ended |",
                "|---|---|---:|---|---|---|---|---|",
            ]
        )
        for item in assignment_chain:
            lines.append(
                f"| `{item.id}` | `{item.status.value}` | {item.attempt} | "
                f"`{item.parent_assignment_id or ''}` | "
                f"`{item.failure_reason.value if item.failure_reason else ''}` | "
                f"{item.retry_reason or ''} | `{item.created_at}` | `{item.ended_at or ''}` |"
            )
    else:
        lines.append("No assignments yet.")
    lines.append("")

    comments = store.list_comments(ticket.id)
    lines.extend(["## Comments", ""])
    if comments:
        for comment in comments:
            lines.append(
                f"- `{comment.created_at}` `{comment.kind.value}` {comment.author}: {comment.body}"
            )
    else:
        lines.append("No comments yet.")
    lines.append("")

    runtime_events = store.list_runtime_events_for_ticket(ticket.id)
    backlog_updates = store.list_backlog_updates_for_ticket(ticket.id)
    lines.extend(["## Backlog Update Trace", ""])
    if backlog_updates:
        for update in backlog_updates:
            lines.append(
                f"- `{update.created_at}` `{update.trigger_type.value}` `{update.id}` - {update.rationale}"
            )
            for change in update.ticket_changes:
                if change.ticket_id == ticket.id:
                    lines.append(
                        f"  - `{change.change_type.value}` {change.before_status or ''} "
                        f"-> {change.after_status or ''}: {change.reason}"
                    )
    else:
        lines.append("No backlog updates for this ticket.")
    lines.append("")
    lines.extend(["## Runtime Journal", ""])
    if runtime_events:
        for event in runtime_events[-12:]:
            lines.append(
                f"- `{event.timestamp}` `{event.stage}:{event.event_type}` "
                f"{event.actor} `{event.idempotency_key}`"
            )
    else:
        lines.append("No runtime journal events yet.")
    lines.append("")

    handoffs = store.list_handoffs_for_ticket(ticket.id)
    lines.extend(["### Agent Handoffs", ""])
    if handoffs:
        lines.extend(["| Handoff | Status | Reason | Payload | Created |", "|---|---|---|---|---|"])
        for handoff in handoffs:
            lines.append(
                f"| {handoff.from_agent} -> {handoff.to_agent} | "
                f"`{handoff.status.value}` | {handoff.reason} | "
                f"`{handoff.payload_ref or ''}` | `{handoff.created_at}` |"
            )
    else:
        lines.append("No Agent handoffs yet.")
    lines.append("")

    open_assignments = store.list_open_assignments()
    stale_locks = [lock for lock in list_locks(store) if lock.stale]
    heartbeats = store.list_worker_heartbeats()
    lines.extend(["## Daemon / Worker", ""])
    lines.append(f"- Open assignments: `{len(open_assignments)}`")
    lines.append(f"- Stale lock warnings: `{len(stale_locks)}`")
    if heartbeats:
        for heartbeat in heartbeats:
            lines.append(
                f"- Worker `{heartbeat.runtime_id}` status=`{heartbeat.status.value}` "
                f"stage=`{heartbeat.current_stage or ''}` ticket=`{heartbeat.current_ticket_key or ''}` "
                f"assignment=`{heartbeat.current_assignment_id or ''}` "
                f"heartbeat_at=`{heartbeat.heartbeat_at}` "
                f"stale=`{str(_is_stale_heartbeat(heartbeat)).lower()}`"
            )
    else:
        lines.append("- Worker heartbeat: `missing`")
    if runtime_events:
        last = runtime_events[-1]
        lines.append(f"- Latest daemon event: `{last.stage}:{last.event_type}`")
    lines.append("")

    runtime_capability = _latest_json_artifact(store, artifacts, ArtifactType.RUNTIME_CAPABILITY)
    lines.extend(["### Runtime Capability", ""])
    if runtime_capability:
        lines.append(f"- Path: `{_latest_artifact_path(artifacts, ArtifactType.RUNTIME_CAPABILITY)}`")
        for capability in runtime_capability.get("capabilities", []):
            lines.append(
                f"- `{capability.get('backend_name')}` available=`{str(capability.get('available')).lower()}` "
                f"external=`{str(capability.get('external_execution_enabled')).lower()}`"
            )
    else:
        lines.append("No runtime capability snapshot found.")
    lines.append("")

    project_resources = _latest_json_artifact(store, artifacts, ArtifactType.PROJECT_RESOURCES)
    lines.extend(["### Project Resources", ""])
    if project_resources:
        lines.append(f"- Path: `{_latest_artifact_path(artifacts, ArtifactType.PROJECT_RESOURCES)}`")
        for resource in project_resources.get("resources", []):
            ref = resource.get("resource_ref", {})
            target = ref.get("local_path") or ref.get("url") or ref
            lines.append(f"- `{resource.get('resource_type')}` {resource.get('label') or ''}: `{target}`")
    else:
        lines.append("No project resources snapshot found.")
    lines.append("")

    route_decision = _latest_json_artifact(store, artifacts, ArtifactType.ROUTE_DECISION)
    lines.extend(["### Route Decision", ""])
    if route_decision:
        lines.append(f"- Path: `{_latest_artifact_path(artifacts, ArtifactType.ROUTE_DECISION)}`")
        lines.append(f"- Backend: `{route_decision.get('backend_name')}`")
        lines.append(f"- Planner: `{route_decision.get('planner_name')}`")
        lines.append(f"- Target repo: `{route_decision.get('target_repo_path')}`")
        lines.append(f"- Reason: {route_decision.get('reason', '')}")
    else:
        lines.append("No route decision artifact found.")
    lines.append("")

    skills = route_decision.get("skill_refs", []) if route_decision else []
    lines.extend(["### Build Skills", ""])
    if skills:
        for skill in skills:
            lines.append(f"- `{skill}`")
    else:
        lines.append("No BuildSkill references found.")
    lines.append("")

    if ticket.build_packet_id:
        packet = store.load_build_packet(ticket.build_packet_id)
        handoff = _latest_artifact(artifacts, ArtifactType.CODEX_HANDOFF)
        quality = packet.metadata.get("quality", {})
        lines.extend(
            [
                "### Build Packet Summary",
                "",
                f"- Decision: `{packet.build_decision.value}`",
                f"- Evidence count: `{len(packet.evidence)}`",
                f"- Quality score: `{quality.get('overall_quality', '')}`",
                f"- Evidence coverage: `{quality.get('evidence_coverage_score', '')}`",
                f"- Task clarity: `{quality.get('task_clarity_score', '')}`",
                f"- Scope risk: `{quality.get('scope_risk_score', '')}`",
                f"- Planner mode: `{packet.metadata.get('planner_mode', '')}`",
                f"- Project relevance: {packet.project_relevance}",
                f"- Handoff artifact: `{handoff.path if handoff else 'missing'}`",
                "",
            ]
        )
    if ticket.metadata.get("execution_result_id"):
        execution = store.load_execution_result(ticket.metadata["execution_result_id"])
        diff_artifact = _latest_artifact(artifacts, ArtifactType.GIT_DIFF)
        changed_artifact = _latest_artifact(artifacts, ArtifactType.CHANGED_FILES)
        test_artifact = _latest_artifact(artifacts, ArtifactType.TEST_OUTPUT)
        lines.extend(
            [
                "### Execution",
                "",
                f"- Backend: `{execution.backend_name}`",
                f"- External execution enabled: `{str(ticket.metadata.get('external_execution_enabled', False)).lower()}`",
                f"- Blocked: `{str(execution.blocked).lower()}`",
                f"- Block reason: {execution.block_reason or 'none'}",
                f"- Exit code: `{execution.exit_code}`",
                f"- Test command: `{execution.test_command}`",
                f"- Test exit code: `{execution.test_exit_code}`",
                f"- Changed files: `{', '.join(execution.changed_files)}`",
                f"- Diff captured: `{str(bool(execution.git_diff)).lower()}`",
                f"- Diff artifact: `{diff_artifact.path if diff_artifact else 'missing'}`",
                f"- Changed files artifact: `{changed_artifact.path if changed_artifact else 'missing'}`",
                f"- Test output artifact: `{test_artifact.path if test_artifact else 'missing'}`",
                "",
            ]
        )
        lines.extend(_provider_audit_artifact_lines(store, artifacts))
    lines.extend(
        [
            "### Agent Run Timeline",
            "",
            "| Started | Agent | Role | Attempt | Backend | Status | Summary |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for run_id in ticket.agent_run_ids:
        run = store.load_run(run_id)
        lines.append(
            f"| {run.started_at or ''} | {run.agent_name} | {run.agent_role} | "
            f"{run.attempt} | {run.backend_name or ''} | {run.status.value} | "
            f"{run.output_summary or ''} |"
        )

    lines.extend(["", "### Artifacts", ""])
    for artifact in artifacts:
        lines.append(
            f"- `{artifact.artifact_type.value}`: `{artifact.path}` - {artifact.summary}"
        )

    review = _latest_json_artifact(store, artifacts, ArtifactType.REVIEW_REPORT)
    lines.extend(["", "### Review Verdict", ""])
    if review:
        lines.append(f"`{review.get('verdict', 'missing')}`")
        if review.get("failed_checks"):
            lines.append("")
            lines.append("Failed checks:")
            for check in review["failed_checks"]:
                lines.append(f"- {check}")
    else:
        lines.append("No review report found.")

    feishu = _latest_json_artifact(store, artifacts, ArtifactType.FEISHU_WRITE_PLAN)
    lines.extend(["", "### Feishu Write Plan", ""])
    if feishu:
        lines.append(f"- Dry-run: `{str(feishu.get('dry_run')).lower()}`")
        lines.append(f"- Path: `{_latest_artifact_path(artifacts, ArtifactType.FEISHU_WRITE_PLAN)}`")
        lines.append(f"- Run summary: {feishu.get('run_summary', '')}")
        lines.append("- Proposed tasks:")
        for task in feishu.get("proposed_tasks", []):
            lines.append(f"  - {task.get('title', 'Untitled')}")
    else:
        lines.append("No Feishu write plan found.")

    memory = _latest_json_artifact(store, artifacts, ArtifactType.MEMORY_RECORD)
    lines.extend(["", "### Memory", ""])
    if memory:
        lines.append(f"- Memory record: `{memory.get('id', 'missing')}`")
        lines.append(f"- Path: `{_latest_artifact_path(artifacts, ArtifactType.MEMORY_RECORD)}`")
        lines.append(f"- Decision: {memory.get('decision_log_entry', '')}")
    else:
        lines.append("No local memory record found.")

    next_tickets = _latest_json_artifact(store, artifacts, ArtifactType.NEXT_TICKETS)
    lines.extend(["", "### Next Tickets", ""])
    if next_tickets:
        lines.append(f"- Path: `{_latest_artifact_path(artifacts, ArtifactType.NEXT_TICKETS)}`")
        for item in next_tickets.get("next_tickets", []):
            lines.append(f"- `{item.get('priority', 'medium')}` {item.get('title', 'Untitled')}")
    else:
        lines.append("No generated next tickets found.")

    lines.extend(["", "### Event Log", ""])
    for event in ticket.event_log:
        lines.append(
            f"- `{event.timestamp}` {event.actor}: {event.event_type} - {event.summary}"
        )
    lines.extend(["", "### Progress Events", ""])
    for event in ticket.event_log:
        if event.event_type in {
            "route_decision",
            "execution_started",
            "execution_finished",
            "review_started",
            "review_finished",
            "memory_written",
            "next_tickets_generated",
            "board_exported",
        }:
            lines.append(
                f"- `{event.timestamp}` `{event.event_type}` {event.summary}"
            )
    lines.append("")
    return lines


def _provider_audit_artifact_lines(store: AriadneStore, artifacts: list) -> list[str]:
    manifest_artifact = _latest_artifact(artifacts, ArtifactType.ORCHESTRATOR_RESULT)
    manifest = _latest_json_artifact(store, artifacts, ArtifactType.ORCHESTRATOR_RESULT)
    execution_log = _latest_artifact(artifacts, ArtifactType.EXECUTION_LOG)
    git_diff = _latest_artifact(artifacts, ArtifactType.GIT_DIFF)
    changed_files = _latest_artifact(artifacts, ArtifactType.CHANGED_FILES)
    test_output = _latest_artifact(artifacts, ArtifactType.TEST_OUTPUT)
    lines = ["### Provider Audit Artifacts", ""]
    if manifest_artifact:
        lines.append(f"- Orchestrator result: `{manifest_artifact.path}`")
    else:
        lines.append("- Orchestrator result: `missing`")
    lines.append(f"- Execution log: `{execution_log.path if execution_log else 'missing'}`")
    lines.append(f"- Git diff: `{git_diff.path if git_diff else 'missing'}`")
    lines.append(f"- Changed files: `{changed_files.path if changed_files else 'missing'}`")
    lines.append(f"- Test output: `{test_output.path if test_output else 'missing'}`")
    if manifest:
        lines.append(f"- Backend: `{manifest.get('backend_name', 'missing')}`")
        lines.append(f"- Execution result: `{manifest.get('execution_result_id', 'missing')}`")
        lines.append(f"- Review report: `{manifest.get('review_report_id', 'missing')}`")
        lines.append(f"- Review verdict: `{manifest.get('review_verdict', 'missing')}`")
        lines.append(
            "- External execution enabled: "
            f"`{str(manifest.get('external_execution_enabled', False)).lower()}`"
        )
        lines.append(f"- Confirm execution: `{str(manifest.get('confirm_execution', False)).lower()}`")
        artifacts_payload = manifest.get("artifacts", {})
        for label, key in [
            ("Memory", "memory_path"),
            ("Feishu dry-run", "feishu_plan_path"),
            ("Next tickets", "next_tickets_path"),
            ("Board", "board_path"),
        ]:
            lines.append(f"- {label}: `{artifacts_payload.get(key, 'missing')}`")
    lines.append("")
    return lines


def _latest_json_artifact(store: AriadneStore, artifacts: list, artifact_type: ArtifactType) -> dict | None:
    for artifact in reversed(artifacts):
        if artifact.artifact_type is artifact_type:
            return json.loads(Path(artifact.path).read_text(encoding="utf-8"))
    return None


def _latest_artifact(artifacts: list, artifact_type: ArtifactType):
    for artifact in reversed(artifacts):
        if artifact.artifact_type is artifact_type:
            return artifact
    return None


def _latest_artifact_path(artifacts: list, artifact_type: ArtifactType) -> str:
    artifact = _latest_artifact(artifacts, artifact_type)
    return artifact.path if artifact else "missing"


def _html_from_markdown(markdown: str) -> str:
    body = markdown.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        "<title>Ariadne Build Board</title>"
        "<style>body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;"
        "max-width:1100px;margin:40px auto;line-height:1.5}"
        "pre{white-space:pre-wrap;background:#f6f8fa;padding:16px;border-radius:8px}"
        "</style></head><body><pre>"
        + body
        + "</pre></body></html>\n"
    )


def _is_stale_heartbeat(heartbeat: WorkerHeartbeat, stale_after_seconds: int = 120) -> bool:
    try:
        heartbeat_at = datetime.fromisoformat(heartbeat.heartbeat_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    return (datetime.now(UTC) - heartbeat_at).total_seconds() > stale_after_seconds
