from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path

from ariadne_ltb.local_safety import validate_target_repo_path
from ariadne_ltb.models import ExecutionContext, ExecutionPermissionProfile, FailureReason, stable_id

DEFAULT_ENV_ALLOWLIST = ("PATH", "HOME", "TMPDIR", "PYTHONPATH")
DEFAULT_NETWORK_POLICY = "disabled_by_default_for_fake_and_shell"
DEFAULT_GIT_POLICY = "block_commit_push_merge_pr"
DANGEROUS_GIT_OPERATIONS = ("commit", "push", "merge", "rebase", "reset", "checkout", "switch", "pull")


@dataclass(frozen=True)
class PermissionValidation:
    valid: bool
    reason: str = ""
    failure_reason: FailureReason | None = None


def build_execution_permission_profile(
    *,
    ticket_id: str,
    ticket_key: str,
    backend_name: str,
    target_repo_path: str,
    allowed_paths: list[str],
    external_execution_enabled: bool,
    confirm_execution: bool,
    command: str,
    test_command: str,
) -> ExecutionPermissionProfile:
    return ExecutionPermissionProfile(
        id=stable_id("permission_profile", ticket_id, backend_name, target_repo_path),
        ticket_id=ticket_id,
        ticket_key=ticket_key,
        backend_name=backend_name,
        target_repo_path=str(Path(target_repo_path).resolve()),
        allowed_paths=allowed_paths,
        env_allowlist=list(DEFAULT_ENV_ALLOWLIST),
        network_policy=DEFAULT_NETWORK_POLICY,
        git_operations_policy=DEFAULT_GIT_POLICY,
        dangerous_git_operations=list(DANGEROUS_GIT_OPERATIONS),
        external_execution_enabled=external_execution_enabled,
        confirm_execution=confirm_execution,
        command=command,
        test_command=test_command,
    )


def permission_profile_handoff_section(profile: ExecutionPermissionProfile, artifact_path: str) -> str:
    allowed = "\n".join(f"- `{path}`" for path in profile.allowed_paths) or "- none"
    return f"""

## Execution Permission Profile

- Profile artifact: `{artifact_path}`
- Target repo: `{profile.target_repo_path}`
- Backend: `{profile.backend_name}`
- Allowed paths:
{allowed}
- Environment allowlist: `{", ".join(profile.env_allowlist)}`
- Network policy: `{profile.network_policy}`
- Git operations policy: `{profile.git_operations_policy}`
- Dangerous git operations blocked: `{", ".join(profile.dangerous_git_operations)}`
- External execution enabled: `{str(profile.external_execution_enabled).lower()}`
- Confirm execution: `{str(profile.confirm_execution).lower()}`
"""


def validate_execution_context_permissions(context: ExecutionContext) -> PermissionValidation:
    target = validate_target_repo_path(context.target_repo_path)
    if not target.valid:
        return PermissionValidation(False, target.reason, target.failure_reason)
    path_validation = validate_allowed_paths(context.allowed_paths)
    if not path_validation.valid:
        return path_validation
    command_validation = validate_command_git_policy(context.command)
    if not command_validation.valid:
        return command_validation
    return PermissionValidation(True)


def validate_allowed_paths(allowed_paths: list[str]) -> PermissionValidation:
    for path in allowed_paths:
        if not path:
            return PermissionValidation(False, "allowed paths cannot contain empty entries", FailureReason.SCOPE_VIOLATION)
        candidate = Path(path)
        if candidate.is_absolute():
            return PermissionValidation(
                False,
                f"allowed path must be relative to target repo: {path}",
                FailureReason.SCOPE_VIOLATION,
            )
        if ".." in candidate.parts:
            return PermissionValidation(
                False,
                f"allowed path cannot escape target repo: {path}",
                FailureReason.SCOPE_VIOLATION,
            )
    return PermissionValidation(True)


def validate_command_git_policy(command: str) -> PermissionValidation:
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        return PermissionValidation(False, f"command cannot be parsed safely: {exc}", FailureReason.SCOPE_VIOLATION)
    if len(tokens) >= 2 and tokens[0] == "git" and tokens[1] in DANGEROUS_GIT_OPERATIONS:
        return PermissionValidation(
            False,
            f"dangerous git operation blocked by permission profile: git {tokens[1]}",
            FailureReason.SCOPE_VIOLATION,
        )
    return PermissionValidation(True)


def validate_changed_files(allowed_paths: list[str], changed_files: list[str]) -> PermissionValidation:
    if "." in allowed_paths:
        return PermissionValidation(True)
    for changed in changed_files:
        if not _is_path_allowed(changed, allowed_paths):
            return PermissionValidation(
                False,
                f"changed file is outside allowed paths: {changed}",
                FailureReason.SCOPE_VIOLATION,
            )
    return PermissionValidation(True)


def _is_path_allowed(path: str, allowed_paths: list[str]) -> bool:
    normalized = path.strip("/")
    for allowed in allowed_paths:
        allowed_normalized = allowed.strip("/")
        if normalized == allowed_normalized or normalized.startswith(f"{allowed_normalized}/"):
            return True
    return False
