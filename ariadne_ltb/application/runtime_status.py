from __future__ import annotations

from ariadne_ltb.application.dtos import RuntimeCapabilityDTO
from ariadne_ltb.application.mappers import runtime_capability_dto
from ariadne_ltb.domain.runtime_policy import product_runtime_capabilities
from ariadne_ltb.runtime import collect_runtime_capabilities
from ariadne_ltb.storage import AriadneStore


class RuntimeStatusService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def snapshot(self, include_internal: bool = False) -> list[RuntimeCapabilityDTO]:
        capabilities = collect_runtime_capabilities()
        self.store.save_runtime_capabilities(capabilities)
        exposed = capabilities if include_internal else product_runtime_capabilities(capabilities)
        return [runtime_capability_dto(capability) for capability in exposed]
