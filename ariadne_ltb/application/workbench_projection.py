from __future__ import annotations

from ariadne_ltb.application.dtos import WorkbenchDTO
from ariadne_ltb.application.daemon_control import DaemonControlService
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
from ariadne_ltb.application.project_goals import ProjectGoalService
from ariadne_ltb.application.runtime_status import RuntimeStatusService
from ariadne_ltb.application.source_understanding import build_source_events, build_source_understandings
from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.inbox import refresh_inbox
from ariadne_ltb.skills import discover_build_skills
from ariadne_ltb.storage import AriadneStore


class WorkbenchProjectionService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def get(self, include_internal_backends: bool = False) -> WorkbenchDTO:
        inbox_items = refresh_inbox(self.store)
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
            tickets=[ticket_summary(self.store, ticket) for ticket in self.store.list_tickets()],
            assignments=[assignment_dto(assignment) for assignment in self.store.list_assignments()],
            agents=[
                agent_profile_dto(self.store, profile)
                for profile in self.store.ensure_default_agent_profiles()
            ],
            runtime_capabilities=RuntimeStatusService(self.store).snapshot(include_internal_backends),
            target_projects=TargetProjectRegistry(self.store).list(),
            skills=[build_skill_dto(skill) for skill in discover_build_skills(self.store.root)],
            inbox=[inbox_item_dto(self.store, item) for item in inbox_items],
            backlog_previews=[
                backlog_preview_dto(preview)
                for preview in self.store.list_backlog_previews()[-10:]
            ],
            daemon_status=DaemonControlService(self.store).status(),
        )

    def snapshot(self, include_internal_backends: bool = False) -> WorkbenchDTO:
        return self.get(include_internal_backends)
