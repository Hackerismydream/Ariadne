from __future__ import annotations

from pathlib import Path

from ariadne_ltb.application.dtos import TargetProjectDTO
from ariadne_ltb.application.errors import NotFoundError, ValidationAppError
from ariadne_ltb.application.mappers import target_project_dto
from ariadne_ltb.local_safety import validate_target_repo_path
from ariadne_ltb.models import ProjectResource
from ariadne_ltb.storage import AriadneStore


class TargetProjectRegistry:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def register(
        self,
        path: str | Path,
        label: str | None = None,
        target_project_id: str | None = None,
    ) -> TargetProjectDTO:
        validation = validate_target_repo_path(path)
        if not validation.valid:
            raise ValidationAppError(validation.reason, {"path": validation.path})
        resources = self.store.load_project_resources()
        resource = ProjectResource.local_directory(
            target_project_id or "ariadne-local",
            validation.path,
            label=label or Path(validation.path).name,
        )
        if target_project_id:
            resource = resource.model_copy(update={"id": target_project_id})
        by_id = {existing.id: existing for existing in resources}
        by_id[resource.id] = resource
        self.store.save_project_resources(sorted(by_id.values(), key=lambda item: item.label or item.id))
        return target_project_dto(resource)

    def list(self) -> list[TargetProjectDTO]:
        result: list[TargetProjectDTO] = []
        for resource in self.store.load_project_resources():
            if resource.resource_type != "local_directory":
                continue
            validation = validate_target_repo_path(resource.resource_ref.get("local_path", ""))
            result.append(target_project_dto(resource, validation.valid, validation.reason))
        return result

    def resolve_path(self, resource_id: str) -> str:
        for resource in self.store.load_project_resources():
            if resource.id != resource_id:
                continue
            path = resource.resource_ref.get("local_path")
            validation = validate_target_repo_path(path)
            if not validation.valid:
                raise ValidationAppError(validation.reason, {"target_project_id": resource_id, "path": path})
            return validation.path
        raise NotFoundError(f"target project not found: {resource_id}")
