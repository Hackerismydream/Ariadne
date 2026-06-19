from __future__ import annotations

from ariadne_ltb.models import BacklogOperation, BacklogOperationType


def validate_issue_delta_operations(operations: list[BacklogOperation]) -> list[BacklogOperation]:
    for operation in operations:
        validate_issue_delta_operation(operation)
    return operations


def validate_issue_delta_operation(operation: BacklogOperation) -> None:
    if operation.operation_type is not BacklogOperationType.ADD_TICKET:
        return
    metadata = operation.metadata
    _require(metadata, "target_project_id")
    _require(metadata, "build_context_id")
    _require_list(metadata, "evidence_refs")
    _require_list(metadata, "affected_modules")
    _require_list(metadata, "acceptance_criteria")
    _require(metadata, "goal_reason")
    if _is_generic_title(operation.title or ""):
        msg = "generic_issue_title"
        raise ValueError(msg)


def _require(metadata: dict[str, object], key: str) -> None:
    if not metadata.get(key):
        msg = f"missing_{key}"
        raise ValueError(msg)


def _require_list(metadata: dict[str, object], key: str) -> None:
    value = metadata.get(key)
    if not isinstance(value, list) or not value:
        msg = f"missing_{key}"
        raise ValueError(msg)


def _is_generic_title(title: str) -> bool:
    normalized = title.strip().lower()
    return normalized in {"implement stuff", "do work", "build feature", "fix things"}
