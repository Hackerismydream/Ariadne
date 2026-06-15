from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from ariadne_ltb.models import ArtifactType, BuildTicket, TicketStatus
from ariadne_ltb.storage import AriadneStore


def export_board(store: AriadneStore) -> Path:
    store.board_dir.mkdir(parents=True, exist_ok=True)
    board_path = store.board_dir / "index.md"
    tickets = store.list_tickets()
    sections: list[str] = [
        "# Ariadne Build Board",
        "",
        "Static local board export. No server is required.",
        "",
    ]
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

    board_path.write_text("\n".join(sections).rstrip() + "\n", encoding="utf-8")
    return board_path


def _ticket_section(store: AriadneStore, ticket: BuildTicket) -> list[str]:
    lines = [
        f"## {ticket.key} - {ticket.title}",
        "",
        f"- Ticket ID: `{ticket.id}`",
        f"- Status: `{ticket.status.value}`",
        f"- Owner: `{ticket.owner_agent}`",
        f"- Source: `{ticket.source_ref}`",
        "",
        "### Agent Run Timeline",
        "",
        "| Started | Agent | Role | Status | Summary |",
        "|---|---|---|---|---|",
    ]
    for run_id in ticket.agent_run_ids:
        run = store.load_run(run_id)
        lines.append(
            f"| {run.started_at or ''} | {run.agent_name} | {run.agent_role} | "
            f"{run.status.value} | {run.output_summary or ''} |"
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
