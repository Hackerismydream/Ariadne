from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from ariadne_ltb.application.dtos import EnvironmentBlockerDTO, TargetProjectDTO, WorkbenchEnvironmentDTO
from ariadne_ltb.application.project_versions import ProjectVersionService
from ariadne_ltb.models import ProjectResource
from ariadne_ltb.storage import AriadneStore


def build_workbench_environment(store: AriadneStore) -> WorkbenchEnvironmentDTO:
    resources = store.load_project_resources()
    current_version = ProjectVersionService(store).current()
    active = next(
        (resource for resource in resources if current_version and resource.id == current_version.target_project_id),
        None,
    )
    active_dto = _target_project_dto(active) if active else None
    codex_available = shutil.which("codex") is not None
    claude_available = shutil.which("claude") is not None
    external_enabled = os.environ.get("ARIADNE_ENABLE_EXTERNAL_EXECUTION") == "1"
    production_backends = [
        name for name, available in {"codex": codex_available, "claude-code": claude_available}.items() if available
    ]
    blockers: list[EnvironmentBlockerDTO] = []
    if current_version is None:
        blockers.append(EnvironmentBlockerDTO(code="project_version_missing", message="还没有创建或选择当前 Project Version。", severity="error"))
        execution_mode = "api_project_version_missing"
    elif active_dto is None or not active_dto.path_exists:
        blockers.append(EnvironmentBlockerDTO(code="target_missing", message="目标 repo 不存在或未注册。", severity="error"))
        execution_mode = "api_target_missing"
    elif not production_backends:
        blockers.append(EnvironmentBlockerDTO(code="runtime_unavailable", message="本机没有可用 Codex/Claude CLI。", severity="error"))
        execution_mode = "api_runtime_unavailable"
    elif not external_enabled:
        blockers.append(EnvironmentBlockerDTO(code="execution_gate_closed", message="ARIADNE_ENABLE_EXTERNAL_EXECUTION 未开启；可以规划，不能真实执行。"))
        execution_mode = "api_gate_closed"
    else:
        execution_mode = "real_api_ready"
    return WorkbenchEnvironmentDTO(
        connection_mode="api",
        execution_mode=execution_mode,
        read_only=False,
        ariadne_root=str(store.root),
        ariadne_store_path=str(store.root / ".ariadne"),
        active_target_project_id=active.id if active else None,
        active_target_project=active_dto,
        production_backends_available=production_backends,
        selected_backend_recommendation=production_backends[0] if production_backends else None,
        blockers=blockers,
    )


def _target_project_dto(resource: ProjectResource | None) -> TargetProjectDTO | None:
    if resource is None:
        return None
    ref = resource.resource_ref
    path_value = ref.get("path") or ref.get("local_path") or ref.get("target_repo_path")
    path = Path(str(path_value)).expanduser() if path_value else None
    path_exists = bool(path and path.exists())
    git_branch = None
    git_dirty = None
    is_git_repo = False
    if path_exists and path:
        is_git_repo = (path / ".git").exists() or _git(path, "rev-parse", "--is-inside-work-tree") == "true"
        if is_git_repo:
            git_branch = _git(path, "branch", "--show-current") or None
            git_dirty = bool(_git(path, "status", "--short"))
    return TargetProjectDTO(
        id=resource.id,
        label=resource.label or str(ref.get("label") or resource.id),
        available=path_exists,
        disabled_reason="" if path_exists else "target path does not exist",
        metadata={key: value for key, value in ref.items() if key in {"daemon_id", "label", "test_command", "issue_prefix"}},
        local_path=str(path) if path else None,
        path_exists=path_exists,
        is_git_repo=is_git_repo,
        git_branch=git_branch,
        git_dirty=git_dirty,
        test_command=str(ref.get("test_command") or ""),
        issue_prefix=str(ref.get("issue_prefix") or ""),
    )


def _git(path: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=path,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""
