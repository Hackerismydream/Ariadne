from __future__ import annotations

from ariadne_ltb.defaults import OFFLINE_TEST_BACKEND
from ariadne_ltb.models import AriadneModel, RuntimeCapability

PRODUCT_BACKENDS = {"codex", "claude-code"}
FALLBACK_BACKENDS = {OFFLINE_TEST_BACKEND, "dry-run"}
WEB_FORBIDDEN_BACKENDS = {"shell"} | FALLBACK_BACKENDS


class RuntimeProfileValues(AriadneModel):
    planner_name: str
    agent_runtime: str
    backlog_planner_name: str


def resolve_runtime_profile(runtime_profile: str, backend_name: str | None) -> str:
    if runtime_profile == "auto":
        return "production" if backend_name in PRODUCT_BACKENDS else "deterministic"
    if runtime_profile not in {"production", "deterministic"}:
        msg = f"unknown runtime profile: {runtime_profile}"
        raise ValueError(msg)
    return runtime_profile


def runtime_profile_values(runtime_profile: str) -> RuntimeProfileValues:
    if runtime_profile == "production":
        return RuntimeProfileValues(
            planner_name="llm",
            agent_runtime="llm",
            backlog_planner_name="llm",
        )
    if runtime_profile == "deterministic":
        return RuntimeProfileValues(
            planner_name="deterministic",
            agent_runtime="deterministic",
            backlog_planner_name="deterministic",
        )
    msg = f"unknown runtime profile: {runtime_profile}"
    raise ValueError(msg)


def validate_backend_for_source(source: str, backend_name: str | None) -> None:
    if backend_name is None:
        return
    if source == "test" and backend_name in FALLBACK_BACKENDS:
        return
    if source == "cli":
        return
    if backend_name in WEB_FORBIDDEN_BACKENDS:
        msg = f"backend `{backend_name}` is not allowed for browser product actions"
        raise ValueError(msg)
    if backend_name not in PRODUCT_BACKENDS:
        msg = f"unknown browser backend: {backend_name}"
        raise ValueError(msg)


def is_product_backend(backend_name: str) -> bool:
    return backend_name in PRODUCT_BACKENDS


def browser_safe_runtime_capability(capability: RuntimeCapability) -> dict:
    fallback_only = capability.backend_name in FALLBACK_BACKENDS
    product = capability.backend_name in PRODUCT_BACKENDS
    return {
        "backend_name": capability.backend_name,
        "display_name": _display_name(capability.backend_name),
        "available": capability.available,
        "can_assign": product and capability.available,
        "can_run": product and capability.available,
        "fallback_only": fallback_only,
        "confirm_execution_required": capability.confirm_execution_required,
        "external_execution_enabled": capability.external_execution_enabled,
        "command_template_set": capability.command_template_set,
        "disabled_reasons": capability.disabled_reasons,
        "notes": capability.notes,
    }


def product_runtime_capabilities(capabilities: list[RuntimeCapability]) -> list[RuntimeCapability]:
    return [capability for capability in capabilities if is_product_backend(capability.backend_name)]


def _display_name(backend_name: str) -> str:
    return {
        "codex": "CodexBackend",
        "claude-code": "ClaudeCodeBackend",
        "fake-codex": "Offline fallback",
        "dry-run": "Dry-run fallback",
        "shell": "Shell",
    }.get(backend_name, backend_name)
