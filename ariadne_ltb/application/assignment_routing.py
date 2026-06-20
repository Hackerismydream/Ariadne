from __future__ import annotations

from pathlib import Path

from ariadne_ltb.application.assignment_readiness import prepare_assignment_for_claim
from ariadne_ltb.application.handoff_packets import create_handoff_packet
from ariadne_ltb.models import AgentProfile, BuildDecision, BuildTicket, RouteDecision, TicketAssignment, stable_id
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import target_test_command


def prepare_direct_agent_assignment(
    store: AriadneStore,
    *,
    ticket: BuildTicket,
    assignment: TicketAssignment,
    agent: AgentProfile,
    target_project_id: str,
    target_repo_path: str,
) -> TicketAssignment:
    target_repo = str(Path(target_repo_path).resolve())
    packet = store.load_build_packet(ticket.build_packet_id) if ticket.build_packet_id else None
    route_decision = RouteDecision(
        id=stable_id("route", ticket.id, assignment.id, assignment.backend_name or agent.backend_name or ""),
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        planner_name=assignment.planner_name,
        agent_runtime=assignment.agent_runtime,
        backlog_planner_name=assignment.backlog_planner_name,
        backend_name=assignment.backend_name or agent.backend_name or "",
        selected_agent_id=agent.id,
        selected_agent_name=agent.name,
        selected_agent_role=agent.role,
        target_repo_path=target_repo,
        build_decision=packet.build_decision if packet else BuildDecision.CODE_TASK,
        reason=f"Direct assignment routed to {agent.name}.",
    )
    store.save_route_decision(route_decision)
    ticket_for_handoff = ticket.model_copy(
        deep=True,
        update={
            "metadata": ticket.metadata
            | {
                "target_project_id": target_project_id,
                "target_repo_path": target_repo,
                "affected_modules": packet.affected_modules if packet else ticket.metadata.get("affected_modules", []),
                "acceptance_criteria": packet.acceptance_criteria
                if packet
                else ticket.metadata.get("acceptance_criteria", []),
                "tasks": packet.tasks if packet else ticket.metadata.get("tasks", []),
                "test_command": ticket.metadata.get("test_command") or target_test_command(),
            }
        },
    )
    handoff_packet = create_handoff_packet(
        store,
        ticket=ticket_for_handoff,
        route_decision=route_decision,
        target_project_id=target_project_id,
        target_repo_path=target_repo,
    )
    assignment = assignment.model_copy(
        deep=True,
        update={
            "metadata": assignment.metadata
            | {
                "target_project_id": target_project_id,
                "target_repo_path": target_repo,
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
