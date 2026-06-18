from __future__ import annotations

from ariadne_ltb.application.dtos import EvidenceProjectionDTO, ExecutionEvidenceDTO
from ariadne_ltb.storage import AriadneStore


class EvidenceProjectionService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def snapshot(self) -> EvidenceProjectionDTO:
        return EvidenceProjectionDTO(
            execution_results=[
                ExecutionEvidenceDTO(
                    id=result.id,
                    ticket_id=result.ticket_id,
                    backend_name=result.backend_name,
                    dry_run=result.dry_run,
                    blocked=result.blocked,
                    block_reason=result.block_reason,
                    failure_reason=result.failure_reason.value if result.failure_reason else None,
                    exit_code=result.exit_code,
                    changed_files=result.changed_files,
                    test_exit_code=result.test_exit_code,
                    warnings=result.warnings,
                    diff_artifact_id=result.diff_artifact_id,
                    execution_log_artifact_id=result.execution_log_artifact_id,
                )
                for result in self.store.list_execution_results()
            ]
        )
