from __future__ import annotations

from ariadne_ltb.application.dtos import (
    AgentListItemDTO,
    AgentListResponse,
    BuildTeamListItemDTO,
    BuildTeamListResponse,
    SkillListResponse,
)
from ariadne_ltb.application.mappers import build_skill_dto
from ariadne_ltb.defaults import OFFLINE_TEST_BACKEND
from ariadne_ltb.models import AssignmentStatus
from ariadne_ltb.skills import discover_build_skills
from ariadne_ltb.storage import AriadneStore


class WorkbenchAgentsService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def list_agents(self) -> AgentListResponse:
        assignments = self.store.list_assignments()
        agents = []
        for profile in self.store.ensure_default_agent_profiles():
            if profile.backend_name == OFFLINE_TEST_BACKEND:
                continue
            agent_assignments = [assignment for assignment in assignments if assignment.agent_id == profile.id]
            agents.append(
                AgentListItemDTO(
                    id=profile.id,
                    name=profile.name,
                    role=profile.role,
                    backend_name=profile.backend_name,
                    runtime_compatibility=profile.agent_runtime,
                    active_assignment_count=sum(
                        1
                        for assignment in agent_assignments
                        if assignment.status in {AssignmentStatus.CLAIMED, AssignmentStatus.RUNNING}
                    ),
                    blocked_count=sum(1 for assignment in agent_assignments if assignment.status is AssignmentStatus.BLOCKED),
                    configuration={
                        "planner_name": profile.planner_name,
                        "agent_runtime": profile.agent_runtime,
                        "backlog_planner_name": profile.backlog_planner_name,
                        "enabled": profile.enabled,
                        "capabilities": profile.capabilities,
                    },
                )
            )
        return AgentListResponse(agents=agents)

    def list_build_teams(self) -> BuildTeamListResponse:
        return BuildTeamListResponse(
            build_teams=[
                BuildTeamListItemDTO(
                    id=team.id,
                    name=team.name,
                    description=team.description,
                    lead_agent_id=team.lead_agent_id,
                    implementer_agent_id=team.implementer_agent_id,
                    reviewer_agent_id=team.reviewer_agent_id,
                    default_backend_name=team.default_backend_name,
                    skill_refs=team.skill_refs,
                    enabled=team.enabled,
                )
                for team in self.store.ensure_default_build_teams()
            ]
        )

    def list_skills(self) -> SkillListResponse:
        return SkillListResponse(skills=[build_skill_dto(skill) for skill in discover_build_skills(self.store.root)])
