from __future__ import annotations

import subprocess
from pathlib import Path

from ariadne_ltb.application.dtos import TargetProjectDTO
from ariadne_ltb.application.errors import ApplicationError, NotFoundError, ValidationAppError
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
        create_if_missing: bool = False,
        init_git: bool = False,
        test_command: str | None = None,
        issue_prefix: str | None = None,
    ) -> TargetProjectDTO:
        candidate = Path(path).expanduser()
        if not candidate.exists():
            if not create_if_missing:
                raise ApplicationError(
                    "target_path_missing",
                    "The target folder does not exist. Regenerate setup by creating the folder or choose an existing project folder.",
                    422,
                    {"path": str(candidate), "action": "create_folder"},
                )
            candidate.mkdir(parents=True, exist_ok=True)
        if init_git and not (candidate / ".git").exists():
            subprocess.run(["git", "init"], cwd=candidate, check=True, capture_output=True)
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
        metadata = dict(resource.resource_ref)
        if test_command:
            metadata["test_command"] = test_command
        if issue_prefix:
            metadata["issue_prefix"] = issue_prefix.upper()
        resource = resource.model_copy(update={"resource_ref": metadata})
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
