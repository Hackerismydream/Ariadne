from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ariadne_ltb.application.assignment_readiness import prepare_assignment_for_claim
from ariadne_ltb.application.handoff_packets import create_handoff_packet
from ariadne_ltb.journal import runtime_event
from ariadne_ltb.models import (
    Artifact,
    ArtifactType,
    BuildDecision,
    BuildTeam,
    BuildTicket,
    CommentAuthorType,
    CommentKind,
    ProjectResource,
    RouteDecision,
    TicketAssignment,
    TicketStatus,
    stable_id,
)
from ariadne_ltb.runtime import collect_runtime_capabilities
from ariadne_ltb.skills import select_build_skills
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project


@dataclass(frozen=True)
class BuildTeamRouteResult:
    team: BuildTeam
    assignment: TicketAssignment
    route_decision: RouteDecision
    route_artifact: Artifact
    handoff_packet_id: str | None = None


def route_ticket_to_build_team(
    store: AriadneStore,
    ticket: BuildTicket,
    team: BuildTeam,
    backend_name: str | None = None,
    planner_name: str | None = None,
    agent_runtime: str | None = None,
    backlog_planner_name: str | None = None,
    target_repo_path: str | None = None,
    target_project_id: str | None = None,
) -> BuildTeamRouteResult:
    lead = store.resolve_agent_profile(team.lead_agent_id)
    implementer = store.resolve_agent_profile(team.implementer_agent_id)
    selected_backend = backend_name or team.default_backend_name or implementer.backend_name or ""
    selected_planner = planner_name or team.planner_name or implementer.planner_name
    selected_agent_runtime = agent_runtime or team.agent_runtime or implementer.agent_runtime
    selected_backlog_planner = (
        backlog_planner_name or team.backlog_planner_name or implementer.backlog_planner_name
    )
    target_repo = Path(target_repo_path).resolve() if target_repo_path else ensure_demo_target_project(store.root)
    resolved_target_project_id = target_project_id or str(ticket.metadata.get("target_project_id") or "ariadne-local")
    runtime_capability_path = store.save_runtime_capabilities(collect_runtime_capabilities())
    existing_resources = store.load_project_resources()
    project_resources = [
        *existing_resources,
        ProjectResource.local_directory(
            resolved_target_project_id,
            target_repo,
            label=f"{ticket.key} target repository",
        ),
    ]
    project_resources_path = store.save_project_resources(project_resources)
    skill_refs = [
        skill.name
        for skill in select_build_skills(
            store.root,
            agent_roles={"planner", "execution", "reviewer", "memory_feishu"},
            skill_names=set(team.skill_refs) if team.skill_refs else None,
        )
    ] or list(team.skill_refs)
    route_decision = RouteDecision(
        id=stable_id("route", ticket.id, team.id, selected_backend, str(target_repo)),
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        planner_name=selected_planner,
        agent_runtime=selected_agent_runtime,
        backlog_planner_name=selected_backlog_planner,
        backend_name=selected_backend,
        build_team_id=team.id,
        build_team_name=team.name,
        team_role_agent_ids={
            "lead": team.lead_agent_id,
            "implementer": team.implementer_agent_id,
            "reviewer": team.reviewer_agent_id,
            "memory": team.memory_agent_id,
        },
        selected_agent_id=implementer.id,
        selected_agent_name=implementer.name,
        selected_agent_role=implementer.role,
        target_repo_path=str(target_repo),
        build_decision=store.load_build_packet(ticket.build_packet_id).build_decision
        if ticket.build_packet_id
        else BuildDecision.CODE_TASK,
        reason=(
            f"{lead.name} routed {ticket.key} through {team.name} to "
            f"{implementer.name} using backend `{selected_backend}`."
        ),
        permission_profile_id=None,
        skill_refs=skill_refs,
        resource_refs=[resource.id for resource in project_resources],
    )
    route_artifact = store.write_artifact(
        ticket.id,
        "build_lead",
        ArtifactType.ROUTE_DECISION,
        "route_decision.json",
        route_decision.model_dump_json(indent=2) + "\n",
        "Build Team route decision",
        metadata={
            "build_team_id": team.id,
            "selected_agent_id": implementer.id,
            "backend_name": selected_backend,
            "runtime_capability_path": str(runtime_capability_path),
            "project_resources_path": str(project_resources_path),
        },
    )
    store.save_route_decision(route_decision, artifact_id=route_artifact.id)
    assignment = store.create_assignment(
        ticket,
        implementer,
        backend_name=selected_backend,
        planner_name=selected_planner,
        agent_runtime=selected_agent_runtime,
        backlog_planner_name=selected_backlog_planner,
        assigned_by=lead.name,
    )
    assignment = assignment.model_copy(
        deep=True,
        update={
            "planner_name": selected_planner,
            "agent_runtime": selected_agent_runtime,
            "backlog_planner_name": selected_backlog_planner,
            "metadata": assignment.metadata
            | {
                "build_team_id": team.id,
                "build_team_name": team.name,
                "lead_agent_id": lead.id,
                "route_decision_artifact_id": route_artifact.id,
                "route_decision_id": route_decision.id,
                "target_project_id": resolved_target_project_id,
                "target_repo_path": str(target_repo),
                "agent_runtime": selected_agent_runtime,
                "backlog_planner_name": selected_backlog_planner,
            },
        },
    )
    store.save_assignment(assignment)
    handoff_packet = create_handoff_packet(
        store,
        ticket=ticket,
        route_decision=route_decision,
        target_project_id=resolved_target_project_id,
        target_repo_path=str(target_repo),
    )
    assignment = assignment.model_copy(
        deep=True,
        update={
            "metadata": assignment.metadata
            | {
                "handoff_packet_id": handoff_packet.id,
                "handoff_packet_path": handoff_packet.markdown_path,
                "handoff_hash": handoff_packet.packet_hash,
            }
        },
    )
    store.save_assignment(assignment)
    assignment = prepare_assignment_for_claim(
        store,
        assignment,
        ticket,
        route_decision_id=route_decision.id,
        handoff_packet_id=handoff_packet.id,
        permission_profile_id=route_decision.permission_profile_id,
        authorization_id=stable_id("runtime_authorization", assignment.id, route_decision.id),
    )
    routed_ticket = (
        store.load_ticket(ticket.id)
        .with_artifacts([route_artifact])
        .append_event(
            "route_decision",
            "Build Lead",
            route_decision.reason,
            payload_ref=route_artifact.id,
        )
        .with_status(
            TicketStatus.READY_FOR_EXECUTION
            if selected_backend == "fake-codex"
            else TicketStatus.WAITING_APPROVAL,
            "Build Lead",
            f"Routed to {implementer.name} through {team.name}.",
        )
        .model_copy(
            deep=True,
            update={
                "metadata": store.load_ticket(ticket.id).metadata
                | {
                    "assigned_team_id": team.id,
                    "assigned_team_name": team.name,
                    "assigned_agent_id": implementer.id,
                    "assigned_agent_name": implementer.name,
                    "latest_assignment_id": assignment.id,
                    "latest_route_decision_artifact_id": route_artifact.id,
                    "latest_handoff_packet_id": handoff_packet.id,
                }
            },
        )
    )
    store.save_ticket(routed_ticket)
    store.add_comment(
        routed_ticket,
        CommentAuthorType.AGENT,
        "Build Lead",
        CommentKind.ROUTE,
        route_decision.reason,
        payload_ref=route_artifact.id,
        thread_id=assignment.id,
    )
    store.append_runtime_event(
        runtime_event(
            routed_ticket,
            "local",
            "route",
            "succeeded",
            "Build Lead",
            assignment_id=assignment.id,
            payload_ref=route_artifact.id,
            metadata={
                "build_team_id": team.id,
                "selected_agent_id": implementer.id,
                "backend_name": selected_backend,
                "agent_runtime": selected_agent_runtime,
                "backlog_planner_name": selected_backlog_planner,
                "reason": route_decision.reason,
                "handoff_packet_id": handoff_packet.id,
            },
        )
    )
    return BuildTeamRouteResult(team, assignment, route_decision, route_artifact, handoff_packet.id)
