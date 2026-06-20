from __future__ import annotations

from hashlib import sha256

from ariadne_ltb.models import BuildTicket, HandoffPacket, RouteDecision, stable_id
from ariadne_ltb.storage import AriadneStore


def create_handoff_packet(
    store: AriadneStore,
    *,
    ticket: BuildTicket,
    route_decision: RouteDecision,
    target_project_id: str,
    target_repo_path: str,
) -> HandoffPacket:
    build_packet = store.load_build_packet(ticket.build_packet_id) if ticket.build_packet_id else None
    criteria = [str(item) for item in ticket.metadata.get("acceptance_criteria") or []]
    if not criteria and build_packet is not None:
        criteria = [str(item) for item in build_packet.acceptance_criteria]
    affected = [str(item) for item in ticket.metadata.get("affected_modules") or []]
    if not affected and build_packet is not None:
        affected = [str(item) for item in build_packet.affected_modules]
    evidence_refs = [str(item) for item in ticket.metadata.get("evidence_refs") or []]
    tasks = [str(item) for item in ticket.metadata.get("tasks") or []]
    if not tasks and build_packet is not None:
        tasks = [str(item) for item in build_packet.tasks]
    test_command = str(ticket.metadata.get("test_command") or _target_test_command(store, target_project_id))
    markdown = _render_markdown(
        ticket,
        route_decision,
        target_repo_path,
        tasks,
        criteria,
        affected,
        evidence_refs,
        test_command,
    )
    packet_hash = sha256(markdown.encode("utf-8")).hexdigest()
    packet = HandoffPacket(
        id=stable_id("handoff_packet", ticket.id, route_decision.id, packet_hash),
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        route_decision_id=route_decision.id,
        build_context_id=str(ticket.metadata.get("build_context_id") or "") or None,
        target_project_id=target_project_id,
        target_repo_path=target_repo_path,
        allowed_paths=affected,
        forbidden_actions=[
            "Do not commit.",
            "Do not push.",
            "Do not copy reference repository source code.",
        ],
        acceptance_criteria=criteria,
        test_command=test_command,
        evidence_refs=evidence_refs,
        markdown_path="",
        packet_hash=packet_hash,
    )
    return store.save_handoff_packet(packet, markdown)


def _target_test_command(store: AriadneStore, target_project_id: str) -> str:
    for resource in store.load_project_resources():
        if resource.id == target_project_id:
            return str(resource.resource_ref.get("test_command") or "python3.11 -m pytest")
    return "python3.11 -m pytest"


def _render_markdown(
    ticket: BuildTicket,
    route_decision: RouteDecision,
    target_repo_path: str,
    tasks: list[str],
    criteria: list[str],
    affected: list[str],
    evidence_refs: list[str],
    test_command: str,
) -> str:
    task = ticket.description or ticket.summary or ticket.title
    lines = [
        f"# {ticket.key}: {ticket.title}",
        "",
        "## Target Repository",
        target_repo_path,
        "",
        "## Route",
        f"- Backend: `{route_decision.backend_name}`",
        f"- Planner: `{route_decision.planner_name}`",
        f"- Agent runtime: `{route_decision.agent_runtime}`",
        "",
        "## Task",
        task,
        "",
        "## Planner Tasks",
        *[f"- {item}" for item in tasks],
        "",
        "## Allowed Paths",
        *[f"- `{item}`" for item in affected],
        "",
        "## Acceptance Criteria",
        *[f"- {item}" for item in criteria],
        "",
        "## Test Command",
        f"`{test_command}`",
        "",
        "## Evidence References",
        *[f"- `{item}`" for item in evidence_refs],
        "",
        "## Forbidden Actions",
        "- Do not commit.",
        "- Do not push.",
        "- Do not copy source code from reference repositories.",
    ]
    return "\n".join(lines).strip() + "\n"
