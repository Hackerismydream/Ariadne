from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from ariadne_ltb.models import ArtifactType, BuildTicket, TicketStatus
from ariadne_ltb.storage import AriadneStore


def export_board(store: AriadneStore) -> Path:
    store.board_dir.mkdir(parents=True, exist_ok=True)
    board_path = store.board_dir / "index.md"
    html_path = store.board_dir / "index.html"
    tickets = store.list_tickets()
    sections: list[str] = [
        "# Ariadne Build Board",
        "",
        "Static local board export. No server is required.",
        "",
        "`learning input -> build decision -> coding execution -> review -> memory`",
        "",
    ]
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
    if ticket.build_packet_id:
        packet = store.load_build_packet(ticket.build_packet_id)
        lines.extend(
            [
                "### Build Packet Summary",
                "",
                f"- Decision: `{packet.build_decision.value}`",
                f"- Evidence count: `{len(packet.evidence)}`",
                f"- Project relevance: {packet.project_relevance}",
                "",
            ]
        )
    if ticket.metadata.get("execution_result_id"):
        execution = store.load_execution_result(ticket.metadata["execution_result_id"])
        lines.extend(
            [
                "### Execution",
                "",
                f"- Backend: `{execution.backend_name}`",
                f"- Exit code: `{execution.exit_code}`",
                f"- Test exit code: `{execution.test_exit_code}`",
                f"- Changed files: `{', '.join(execution.changed_files)}`",
                f"- Diff captured: `{str(bool(execution.git_diff)).lower()}`",
                "",
            ]
        )
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
    artifacts = [store.load_artifact(artifact_id) for artifact_id in ticket.artifact_ids]
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
        lines.append(f"- Decision: {memory.get('decision_log_entry', '')}")
    else:
        lines.append("No local memory record found.")

    lines.extend(["", "### Event Log", ""])
    for event in ticket.event_log:
        lines.append(
            f"- `{event.timestamp}` {event.actor}: {event.event_type} - {event.summary}"
        )
    lines.append("")
    return lines


def _latest_json_artifact(store: AriadneStore, artifacts: list, artifact_type: ArtifactType) -> dict | None:
    for artifact in reversed(artifacts):
        if artifact.artifact_type is artifact_type:
            return json.loads(Path(artifact.path).read_text(encoding="utf-8"))
    return None


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
