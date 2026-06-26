from __future__ import annotations

from ariadne_ltb.application.current_version_scope import current_version_mainline_tickets
from ariadne_ltb.application.dtos import WorkbenchDTO
from ariadne_ltb.application.daemon_control import DaemonControlService
from ariadne_ltb.application.agent_workflow_projection import build_agent_workflows
from ariadne_ltb.application.issue_projection import build_issue_projection
from ariadne_ltb.application.mappers import (
    agent_profile_dto,
    assignment_dto,
    backlog_preview_dto,
    build_skill_dto,
    inbox_item_dto,
    source_artifact_dto,
    source_document_dto,
    source_evidence_dto,
    ticket_summary,
)
from ariadne_ltb.application.project_inputs import build_project_inputs
from ariadne_ltb.application.project_version_delivery import build_current_version_delivery
from ariadne_ltb.application.project_goals import ProjectGoalService
from ariadne_ltb.application.runtime_status import RuntimeStatusService
from ariadne_ltb.application.source_understanding import build_source_events, build_source_understandings
from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.application.workbench_environment import build_workbench_environment
from ariadne_ltb.inbox import refresh_inbox
from ariadne_ltb.skills import discover_build_skills
from ariadne_ltb.storage import AriadneStore


class WorkbenchProjectionService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def get(self, include_internal_backends: bool = False) -> WorkbenchDTO:
        inbox_items = refresh_inbox(self.store)
        agent_workflows, agent_activities = build_agent_workflows(self.store)
        current_version_delivery = build_current_version_delivery(self.store)
        target_project_id = current_version_delivery.target_project_id if current_version_delivery else None
        current_tickets = current_version_mainline_tickets(self.store, target_project_id)
        current_ticket_ids = {ticket.id for ticket in current_tickets}
        current_ticket_keys = {ticket.key for ticket in current_tickets}
        current_assignments = [
            assignment for assignment in self.store.list_assignments() if assignment.ticket_id in current_ticket_ids
        ]
        current_inbox_items = [
            item for item in inbox_items if item.ticket_id is None or item.ticket_id in current_ticket_ids
        ]
        current_workflows = [
            workflow for workflow in agent_workflows if workflow.ticket_id in current_ticket_ids
        ]
        current_activities = [
            activity
            for activity in agent_activities
            if activity.ticket_id in current_ticket_ids or activity.ticket_key in current_ticket_keys
        ]
        return WorkbenchDTO(
            goals=ProjectGoalService(self.store).list(),
            sources=[source_document_dto(self.store, source) for source in self.store.list_source_documents()],
            source_artifacts=[
                source_artifact_dto(artifact)
                for artifact in self.store.list_source_artifacts()
            ],
            source_evidence=[
                source_evidence_dto(evidence)
                for evidence in self.store.list_source_evidence()
            ],
            source_understandings=build_source_understandings(self.store),
            source_events=build_source_events(self.store),
            tickets=[ticket_summary(self.store, ticket) for ticket in current_tickets],
            assignments=[assignment_dto(assignment) for assignment in current_assignments],
            agents=[
                agent_profile_dto(self.store, agent.to_agent_profile())
                for agent in self.store.list_agent_definitions()
            ],
            runtime_capabilities=RuntimeStatusService(self.store).snapshot(include_internal_backends),
            target_projects=TargetProjectRegistry(self.store).list(),
            skills=[build_skill_dto(skill) for skill in discover_build_skills(self.store.root)],
            inbox=[inbox_item_dto(self.store, item) for item in current_inbox_items],
            backlog_previews=[
                backlog_preview_dto(preview)
                for preview in self.store.list_backlog_previews()[-10:]
            ],
            daemon_status=DaemonControlService(self.store).status(),
            environment=build_workbench_environment(self.store),
            current_version_delivery=current_version_delivery,
            project_inputs=build_project_inputs(self.store),
            issue_projection=build_issue_projection(self.store),
            agent_workflows=current_workflows,
            agent_activities=current_activities,
        )

    def snapshot(self, include_internal_backends: bool = False) -> WorkbenchDTO:
        return self.get(include_internal_backends)
