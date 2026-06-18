from __future__ import annotations

from ariadne_ltb.defaults import OFFLINE_TEST_BACKEND
from ariadne_ltb.models import RuntimeCapability

PRODUCT_BACKENDS = {"codex", "claude-code"}
INTERNAL_BACKENDS = {OFFLINE_TEST_BACKEND, "dry-run", "shell"}


def is_product_backend(backend_name: str) -> bool:
    return backend_name in PRODUCT_BACKENDS


def browser_safe_runtime_capability(capability: RuntimeCapability) -> dict:
    return {
        "backend_name": capability.backend_name,
        "available": capability.available,
        "external_execution_enabled": capability.external_execution_enabled,
        "command_template_set": capability.command_template_set,
        "confirm_execution_required": capability.confirm_execution_required,
        "disabled_reasons": capability.disabled_reasons,
        "notes": capability.notes,
    }


def product_runtime_capabilities(capabilities: list[RuntimeCapability]) -> list[RuntimeCapability]:
    return [capability for capability in capabilities if is_product_backend(capability.backend_name)]
