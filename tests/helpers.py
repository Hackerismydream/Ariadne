from __future__ import annotations

from pathlib import Path

from ariadne_ltb.application.assignment_readiness import (
    ensure_assignment_target_resource,
    prepare_assignment_for_claim,
)
from ariadne_ltb.application.handoff_packets import create_handoff_packet
from ariadne_ltb.models import BuildDecision, RouteDecision, stable_id
from ariadne_ltb.storage import AriadneStore


def ready_assignment_with_handoff(store: AriadneStore, ticket, assignment, target_repo: Path):  # noqa: ANN001
    target_project_id = "ariadne-local"
    ensure_assignment_target_resource(
        store,
        str(target_repo),
        target_project_id=target_project_id,
        label=f"{ticket.key} target repository",
    )
    packet = store.load_build_packet(ticket.build_packet_id) if ticket.build_packet_id else None
    ticket_for_handoff = ticket.model_copy(
        deep=True,
        update={
            "metadata": ticket.metadata
            | {
                "target_project_id": target_project_id,
                "target_repo_path": str(target_repo),
                "affected_modules": packet.affected_modules if packet else [],
                "acceptance_criteria": packet.acceptance_criteria if packet else [],
                "test_command": "python3.11 -m pytest",
            }
        },
    )
    route_decision = RouteDecision(
        id=stable_id("route", ticket.id, assignment.id, assignment.backend_name or ""),
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        planner_name=assignment.planner_name,
        agent_runtime=assignment.agent_runtime,
        backlog_planner_name=assignment.backlog_planner_name,
        backend_name=assignment.backend_name or "",
        selected_agent_id=assignment.agent_id,
        selected_agent_name=assignment.agent_name,
        target_repo_path=str(target_repo),
        build_decision=packet.build_decision if packet else BuildDecision.CODE_TASK,
        reason="Test route decision.",
    )
    store.save_route_decision(route_decision)
    handoff_packet = create_handoff_packet(
        store,
        ticket=ticket_for_handoff,
        route_decision=route_decision,
        target_project_id=target_project_id,
        target_repo_path=str(target_repo),
    )
    assignment = assignment.model_copy(
        deep=True,
        update={
            "metadata": assignment.metadata
            | {
                "target_project_id": target_project_id,
                "target_repo_path": str(target_repo),
                "route_decision_id": route_decision.id,
                "handoff_packet_id": handoff_packet.id,
                "handoff_packet_path": handoff_packet.markdown_path,
                "handoff_hash": handoff_packet.packet_hash,
            }
        },
    )
    store.save_assignment(assignment)
    return prepare_assignment_for_claim(
        store,
        assignment,
        ticket,
        route_decision_id=route_decision.id,
        handoff_packet_id=handoff_packet.id,
        authorization_id=stable_id("runtime_authorization", assignment.id, route_decision.id),
    )
