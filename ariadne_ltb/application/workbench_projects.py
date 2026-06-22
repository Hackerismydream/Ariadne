from __future__ import annotations

from ariadne_ltb.application.dtos import ProjectDetailResponse, ProjectListResponse
from ariadne_ltb.application.errors import NotFoundError
from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.storage import AriadneStore


class WorkbenchProjectsService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def list(self) -> ProjectListResponse:
        return ProjectListResponse(projects=TargetProjectRegistry(self.store).list())

    def detail(self, project_id: str) -> ProjectDetailResponse:
        for project in TargetProjectRegistry(self.store).list():
            if project.id == project_id:
                return ProjectDetailResponse(project=project)
        raise NotFoundError(f"Project not found: {project_id}", {"project_id": project_id})
