from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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


def route_ticket_to_build_team(
    store: AriadneStore,
    ticket: BuildTicket,
    team: BuildTeam,
    backend_name: str | None = None,
    target_repo_path: str | None = None,
) -> BuildTeamRouteResult:
    lead = store.resolve_agent_profile(team.lead_agent_id)
    implementer = store.resolve_agent_profile(team.implementer_agent_id)
    selected_backend = backend_name or team.default_backend_name or implementer.backend_name or ""
    target_repo = Path(target_repo_path).resolve() if target_repo_path else ensure_demo_target_project(store.root)
    runtime_capability_path = store.save_runtime_capabilities(collect_runtime_capabilities())
    project_resources = [
        ProjectResource.local_directory(
            "ariadne-local",
            target_repo,
            label=f"{ticket.key} target repository",
        )
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
        planner_name=team.planner_name,
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
    assignment = store.create_assignment(
        ticket,
        implementer,
        backend_name=selected_backend,
        assigned_by=lead.name,
    )
    assignment = assignment.model_copy(
        deep=True,
        update={
            "planner_name": team.planner_name,
            "metadata": assignment.metadata
            | {
                "build_team_id": team.id,
                "build_team_name": team.name,
                "lead_agent_id": lead.id,
                "route_decision_artifact_id": route_artifact.id,
            },
        },
    )
    store.save_assignment(assignment)
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
                "reason": route_decision.reason,
            },
        )
    )
    return BuildTeamRouteResult(team, assignment, route_decision, route_artifact)
