from __future__ import annotations

from ariadne_ltb.application.dtos import RuntimeCapabilityDTO
from ariadne_ltb.domain.runtime_policy import browser_safe_runtime_capability
from ariadne_ltb.runtime import collect_runtime_capabilities
from ariadne_ltb.storage import AriadneStore


class RuntimeStatusService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def snapshot(self, include_internal: bool = False) -> list[RuntimeCapabilityDTO]:
        capabilities = collect_runtime_capabilities()
        self.store.save_runtime_capabilities(capabilities)
        exposed = [
            capability
            for capability in capabilities
            if include_internal or capability.backend_name != "shell"
        ]
        return [
            RuntimeCapabilityDTO.model_validate(browser_safe_runtime_capability(capability))
            for capability in exposed
        ]
