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
    for key in [
        "target_project_id",
        "build_context_id",
        "context_fingerprint",
    ]:
        _require(metadata, key)
    for key in [
        "source_document_ids",
        "source_artifact_ids",
        "evidence_refs",
        "affected_modules",
        "acceptance_criteria",
    ]:
        _require_list(metadata, key)
    _require(metadata, "goal_reason")
    if _is_generic_title(operation.title or ""):
        msg = "generic_issue_title"
        raise ValueError(msg)
    if _uses_demo_path(metadata):
        msg = "demo_path_not_allowed_in_product_issue"
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


def _uses_demo_path(metadata: dict[str, object]) -> bool:
    affected = metadata.get("affected_modules") or []
    if not isinstance(affected, list):
        return False
    target_project_id = str(metadata.get("target_project_id") or "").lower()
    source_document = metadata.get("source_document")
    source_metadata = source_document.get("metadata", {}) if isinstance(source_document, dict) else {}
    entrypoint = str(source_metadata.get("entrypoint") or "").lower() if isinstance(source_metadata, dict) else ""
    explicit_demo = "demo" in target_project_id or entrypoint == "offline_regression_fixture"
    if explicit_demo:
        return False
    return any("demo_todo" in str(module) or "export-json" in str(module) for module in affected)
