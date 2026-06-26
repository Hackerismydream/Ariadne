from __future__ import annotations

from ariadne_ltb.application.dtos import (
    CreateProjectGoalInput,
    CreateProjectVersionInput,
    ProjectVersionDTO,
)
from ariadne_ltb.application.errors import NotFoundError, ValidationAppError
from ariadne_ltb.application.project_goals import ProjectGoalService
from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.models import ProjectResource, ProjectVersion, stable_id, utc_now
from ariadne_ltb.storage import AriadneStore


class ProjectVersionService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def list(self) -> list[ProjectVersionDTO]:
        versions = sorted(
            self.store.load_project_versions(),
            key=lambda item: (item.selected_at or "", item.updated_at, item.created_at),
            reverse=True,
        )
        return [self._dto(version) for version in versions]

    def current(self) -> ProjectVersionDTO | None:
        version = self._current_model()
        return self._dto(version) if version else None

    def create(self, payload: CreateProjectVersionInput) -> ProjectVersionDTO:
        target_project_id = self._resolve_or_register_target(payload)
        now = utc_now()
        goal = ProjectGoalService(self.store).create(
            CreateProjectGoalInput(
                title=payload.goal_title.strip(),
                north_star=payload.goal_north_star.strip(),
                current_state="Project Version was created from the browser Workbench.",
                target_state=payload.target_state.strip()
                or "Target project advances through source-grounded issues, agent runs, and browser evidence.",
                target_project_id=target_project_id,
                knowledge_inputs=[],
                feedback_signals=["Created from Project Version Workbench entry."],
            )
        )
        version = ProjectVersion(
            id=stable_id("project_version", target_project_id, payload.version_label.strip()),
            target_project_id=target_project_id,
            version_label=payload.version_label.strip(),
            goal_id=goal.id,
            goal_title=goal.title,
            goal_north_star=goal.north_star,
            status="active",
            created_at=now,
            updated_at=now,
            selected_at=now,
        )
        versions = [
            existing.model_copy(update={"selected_at": None})
            for existing in self.store.load_project_versions()
            if existing.id != version.id
        ]
        versions.append(version)
        self.store.save_project_versions(sorted(versions, key=lambda item: (item.target_project_id, item.version_label)))
        return self._dto(version)

    def select(self, version_id: str) -> ProjectVersionDTO:
        versions = self.store.load_project_versions()
        selected = next((version for version in versions if version.id == version_id), None)
        if selected is None:
            raise NotFoundError("project version not found", {"version_id": version_id})
        now = utc_now()
        updated = [
            version.model_copy(update={"selected_at": now, "updated_at": now})
            if version.id == version_id
            else version.model_copy(update={"selected_at": None})
            for version in versions
        ]
        self.store.save_project_versions(updated)
        return self._dto(next(version for version in updated if version.id == version_id))

    def current_target_project_id(self) -> str | None:
        current = self._current_model()
        return current.target_project_id if current else None

    def _current_model(self) -> ProjectVersion | None:
        versions = self.store.load_project_versions()
        if not versions:
            return None
        selected = [version for version in versions if version.selected_at]
        if selected:
            return sorted(selected, key=lambda item: item.selected_at or "")[-1]
        return sorted(versions, key=lambda item: (item.updated_at, item.created_at))[-1]

    def _resolve_or_register_target(self, payload: CreateProjectVersionInput) -> str:
        if payload.target_project_id:
            if self._resource_for(payload.target_project_id) is None:
                raise NotFoundError("target project not found", {"target_project_id": payload.target_project_id})
            return payload.target_project_id
        if not payload.target_repo_path or not payload.target_repo_path.strip():
            raise ValidationAppError("target_repo_required", {"message": "Choose a target project or enter a target repo path."})
        registered = TargetProjectRegistry(self.store).register(
            payload.target_repo_path.strip(),
            payload.target_repo_label.strip() if payload.target_repo_label else None,
            create_if_missing=payload.create_if_missing,
            init_git=payload.init_git,
            test_command=payload.test_command,
            issue_prefix=payload.issue_prefix,
        )
        return registered.id

    def _resource_for(self, target_project_id: str) -> ProjectResource | None:
        return next((resource for resource in self.store.load_project_resources() if resource.id == target_project_id), None)

    def _dto(self, version: ProjectVersion) -> ProjectVersionDTO:
        target_project = next(
            (project for project in TargetProjectRegistry(self.store).list() if project.id == version.target_project_id),
            None,
        )
        return ProjectVersionDTO(
            id=version.id,
            target_project_id=version.target_project_id,
            target_project_label=target_project.label if target_project else None,
            target_project=target_project,
            version_label=version.version_label,
            goal_id=version.goal_id,
            goal_title=version.goal_title,
            goal_north_star=version.goal_north_star,
            status=version.status,
            created_at=version.created_at,
            updated_at=version.updated_at,
            selected_at=version.selected_at,
        )
