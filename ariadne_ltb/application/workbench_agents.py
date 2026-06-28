from __future__ import annotations

from ariadne_ltb.application.dtos import (
    AgentActivityItemDTO,
    AgentActivityResponse,
    AgentCreateInput,
    AgentDetailDTO,
    AgentDetailResponse,
    AgentEnvironmentResponse,
    AgentInstructionsResponse,
    AgentListItemDTO,
    AgentListResponse,
    AgentRunItemDTO,
    AgentRunsResponse,
    AgentRuntimeProfileDTO,
    AgentSkillsResponse,
    AgentTaskItemDTO,
    AgentTasksResponse,
    AgentUpdateInput,
    AgentVisibilityDTO,
    BuildTeamListItemDTO,
    BuildTeamListResponse,
    SkillListResponse,
)
from ariadne_ltb.application.errors import NotFoundError
from ariadne_ltb.application.mappers import build_skill_dto
from ariadne_ltb.application.mappers import assignment_dto
from ariadne_ltb.application.run_events import RunEventService
from ariadne_ltb.inbox import refresh_inbox
from ariadne_ltb.models import AssignmentStatus
from ariadne_ltb.models import AgentDefinition, AgentRuntimeProfile, AgentVisibility, stable_id, utc_now
from ariadne_ltb.skills import discover_build_skills
from ariadne_ltb.storage import AriadneStore


class WorkbenchAgentsService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def list_agents(self) -> AgentListResponse:
        assignments = self.store.list_assignments()
        agents = [self._agent_list_item(agent, assignments) for agent in self.store.list_agent_definitions()]
        return AgentListResponse(agents=agents)

    def create_agent(self, payload: AgentCreateInput) -> AgentDetailResponse:
        created_at = utc_now()
        agent_id = stable_id("agent", payload.name, created_at)
        runtime_profile_id = f"{agent_id}:runtime"
        agent = AgentDefinition(
            agent_id=agent_id,
            name=payload.name.strip(),
            description=payload.description.strip(),
            avatar_seed=payload.name.strip().lower() or agent_id,
            runtime_profile_id=runtime_profile_id,
            runtime_profile=AgentRuntimeProfile(
                profile_id=runtime_profile_id,
                agent_id=agent_id,
                backend=payload.backend,
                model=payload.model,
                working_directory=payload.working_directory,
                environment_keys=sorted(set(payload.environment_keys)),
                reasoning_level=payload.reasoning_level,
                service_tier=payload.service_tier,
            ),
            visibility=AgentVisibility(
                agent_id=agent_id,
                visible=payload.visible,
                team_ids=sorted(set(payload.team_ids)),
            ),
            role="coding_agent",
            instructions=payload.instructions,
            skill_ids=sorted(set(payload.skill_ids)),
            max_concurrent_assignments=payload.max_concurrent_assignments,
            created_at=created_at,
            updated_at=created_at,
        )
        self.store.save_agent_definition(agent)
        return AgentDetailResponse(agent=self._agent_detail(agent))

    def get_agent(self, agent_id: str) -> AgentDetailResponse:
        return AgentDetailResponse(agent=self._agent_detail(self._load_agent(agent_id)))

    def update_agent(self, agent_id: str, payload: AgentUpdateInput) -> AgentDetailResponse:
        agent = self._load_agent(agent_id)
        runtime_profile = agent.runtime_profile
        if runtime_profile and any(
            value is not None
            for value in [
                payload.model,
                payload.working_directory,
                payload.environment_keys,
                payload.reasoning_level,
                payload.service_tier,
            ]
        ):
            runtime_profile = runtime_profile.model_copy(
                deep=True,
                update={
                    key: value
                    for key, value in {
                        "model": payload.model,
                        "working_directory": payload.working_directory,
                        "environment_keys": sorted(set(payload.environment_keys)) if payload.environment_keys is not None else None,
                        "reasoning_level": payload.reasoning_level,
                        "service_tier": payload.service_tier,
                    }.items()
                    if value is not None
                },
            )
        visibility = agent.visibility
        if visibility and (payload.visible is not None or payload.team_ids is not None):
            visibility = visibility.model_copy(
                deep=True,
                update={
                    key: value
                    for key, value in {
                        "visible": payload.visible,
                        "team_ids": sorted(set(payload.team_ids)) if payload.team_ids is not None else None,
                    }.items()
                    if value is not None
                },
            )
        updated = agent.model_copy(
            deep=True,
            update={
                key: value
                for key, value in {
                    "name": payload.name.strip() if payload.name is not None else None,
                    "description": payload.description.strip() if payload.description is not None else None,
                    "status": payload.status,
                    "runtime_profile": runtime_profile,
                    "visibility": visibility,
                    "instructions": payload.instructions,
                    "skill_ids": sorted(set(payload.skill_ids)) if payload.skill_ids is not None else None,
                    "max_concurrent_assignments": payload.max_concurrent_assignments,
                    "updated_at": utc_now(),
                }.items()
                if value is not None
            },
        )
        self.store.save_agent_definition(updated)
        return AgentDetailResponse(agent=self._agent_detail(updated))

    def activity(self, agent_id: str) -> AgentActivityResponse:
        self._load_agent(agent_id)
        items = [
            AgentActivityItemDTO(
                id=event.id,
                timestamp=event.timestamp,
                source=event.source,
                event_type=event.event_type,
                stage=event.stage,
                summary=event.summary,
                ticket_id=event.ticket_id,
                ticket_key=event.ticket_key,
                assignment_id=event.assignment_id,
                ref_id=event.ref_id,
            )
            for event in RunEventService(self.store).agent_assignment_events(agent_id)
        ]
        return AgentActivityResponse(activity=sorted(items, key=lambda item: item.timestamp, reverse=True))

    def tasks(self, agent_id: str) -> AgentTasksResponse:
        self._load_agent(agent_id)
        inbox_by_assignment = {
            item.source_id: item
            for item in refresh_inbox(self.store)
            if item.source_type == "assignment"
        }
        return AgentTasksResponse(
            tasks=[
                self._task_item(assignment, inbox_by_assignment.get(assignment.id))
                for assignment in sorted(self._agent_assignments(agent_id), key=lambda item: item.created_at, reverse=True)
            ]
        )

    def runs(self, agent_id: str) -> AgentRunsResponse:
        agent = self._load_agent(agent_id)
        assignments = self._agent_assignments(agent_id)
        assignment_ids = {assignment.id for assignment in assignments}
        ticket_keys = {ticket.id: ticket.key for ticket in self.store.list_tickets()}
        runs = []
        for run in self.store.list_runs():
            assignment_id = run.metadata.get("assignment_id")
            run_agent_id = run.metadata.get("agent_id")
            if run_agent_id != agent_id and assignment_id not in assignment_ids and run.agent_name != agent.name:
                continue
            failure_reason = run.failure_reason.value if run.failure_reason else None
            runs.append(
                AgentRunItemDTO(
                    id=run.id,
                    ticket_id=run.ticket_id,
                    ticket_key=ticket_keys.get(run.ticket_id),
                    agent_name=run.agent_name,
                    agent_role=run.agent_role,
                    status=run.status.value,
                    lifecycle_state=run.lifecycle_state.value,
                    backend_name=run.backend_name,
                    started_at=run.started_at,
                    ended_at=run.ended_at,
                    failure_reason=failure_reason,
                    error=run.error,
                    assignment_id=assignment_id if isinstance(assignment_id, str) else None,
                )
            )
        return AgentRunsResponse(runs=sorted(runs, key=lambda item: item.started_at or item.ended_at or "", reverse=True))

    def skills(self, agent_id: str) -> AgentSkillsResponse:
        agent = self._load_agent(agent_id)
        all_skills = {skill.id: skill for skill in discover_build_skills(self.store.root)}
        return AgentSkillsResponse(
            skill_ids=agent.skill_ids,
            skills=[build_skill_dto(all_skills[skill_id]) for skill_id in agent.skill_ids if skill_id in all_skills],
        )

    def instructions(self, agent_id: str) -> AgentInstructionsResponse:
        return AgentInstructionsResponse(instructions=self._load_agent(agent_id).instructions)

    def environment(self, agent_id: str) -> AgentEnvironmentResponse:
        agent = self._load_agent(agent_id)
        keys = agent.runtime_profile.environment_keys if agent.runtime_profile else []
        return AgentEnvironmentResponse(environment_keys=keys)

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

    def _load_agent(self, agent_id: str) -> AgentDefinition:
        try:
            return self.store.load_agent_definition(agent_id)
        except FileNotFoundError as exc:
            raise NotFoundError(f"agent not found: {agent_id}") from exc

    def _agent_assignments(self, agent_id: str):
        return [assignment for assignment in self.store.list_assignments() if assignment.agent_id == agent_id]

    def _task_item(self, assignment, inbox_item) -> AgentTaskItemDTO:
        status = _task_status(assignment.status)
        blocker_reason = assignment.blocker or (assignment.failure_reason.value if assignment.failure_reason else None)
        return AgentTaskItemDTO(
            assignment=assignment_dto(assignment),
            task_id=assignment.id,
            ticket_id=assignment.ticket_id,
            ticket_key=assignment.ticket_key,
            agent_id=assignment.agent_id,
            status=status,
            attempt_number=assignment.attempt,
            retry_count=max(0, assignment.attempt - 1),
            blocker_id=inbox_item.id if inbox_item else None,
            blocker_reason=blocker_reason,
            claimed_at=assignment.claimed_at,
            started_at=assignment.started_at,
            completed_at=assignment.ended_at,
            current=status in {"claimed", "running"},
        )

    def _agent_list_item(self, agent: AgentDefinition, assignments) -> AgentListItemDTO:
        agent_assignments = [assignment for assignment in assignments if assignment.agent_id == agent.agent_id]
        runtime_profile = self._runtime_profile_dto(agent)
        visibility = self._visibility_dto(agent)
        return AgentListItemDTO(
            id=agent.agent_id,
            name=agent.name,
            role=agent.role,
            backend_name=agent.runtime_profile.backend if agent.runtime_profile else None,
            runtime_compatibility=agent.runtime_profile.backend if agent.runtime_profile else "not_configured",
            active_assignment_count=sum(
                1
                for assignment in agent_assignments
                if assignment.status
                in {
                    AssignmentStatus.QUEUED,
                    AssignmentStatus.ROUTED,
                    AssignmentStatus.HANDOFF_READY,
                    AssignmentStatus.AWAITING_USER_APPROVAL,
                    AssignmentStatus.READY_TO_CLAIM,
                    AssignmentStatus.CLAIMED,
                    AssignmentStatus.RUNNING,
                }
            ),
            blocked_count=sum(1 for assignment in agent_assignments if assignment.status is AssignmentStatus.BLOCKED),
            description=agent.description,
            avatar_seed=agent.avatar_seed,
            status=agent.status,
            runtime_profile=runtime_profile,
            visibility=visibility,
            skill_ids=agent.skill_ids,
            instructions_present=bool(agent.instructions.strip()),
            updated_at=agent.updated_at,
            configuration={
                "enabled": agent.status == "active",
                "capabilities": agent.skill_ids,
                "max_concurrent_assignments": agent.max_concurrent_assignments,
            },
        )

    def _agent_detail(self, agent: AgentDefinition) -> AgentDetailDTO:
        item = self._agent_list_item(agent, self.store.list_assignments()).model_dump(mode="python")
        return AgentDetailDTO(
            **item,
            instructions=agent.instructions,
            environment_keys=agent.runtime_profile.environment_keys if agent.runtime_profile else [],
        )

    def _runtime_profile_dto(self, agent: AgentDefinition) -> AgentRuntimeProfileDTO | None:
        if not agent.runtime_profile:
            return None
        return AgentRuntimeProfileDTO(
            profile_id=agent.runtime_profile.profile_id,
            agent_id=agent.runtime_profile.agent_id,
            backend=agent.runtime_profile.backend,
            model=agent.runtime_profile.model,
            working_directory=agent.runtime_profile.working_directory,
            environment_keys=agent.runtime_profile.environment_keys,
            reasoning_level=agent.runtime_profile.reasoning_level,
            service_tier=agent.runtime_profile.service_tier,
        )

    def _visibility_dto(self, agent: AgentDefinition) -> AgentVisibilityDTO | None:
        if not agent.visibility:
            return None
        return AgentVisibilityDTO(
            agent_id=agent.visibility.agent_id,
            visible=agent.visibility.visible,
            team_ids=agent.visibility.team_ids,
        )


def _task_status(status: AssignmentStatus) -> str:
    if status in {
        AssignmentStatus.QUEUED,
        AssignmentStatus.ROUTED,
        AssignmentStatus.HANDOFF_READY,
        AssignmentStatus.AWAITING_USER_APPROVAL,
        AssignmentStatus.READY_TO_CLAIM,
    }:
        return "queued"
    if status is AssignmentStatus.CLAIMED:
        return "claimed"
    if status is AssignmentStatus.RUNNING:
        return "running"
    if status is AssignmentStatus.BLOCKED:
        return "blocked"
    if status is AssignmentStatus.DONE:
        return "done"
    if status is AssignmentStatus.FAILED:
        return "failed"
    if status is AssignmentStatus.CANCELLED:
        return "cancelled"
    return status.value
