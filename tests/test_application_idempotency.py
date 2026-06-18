from __future__ import annotations

from pathlib import Path

import pytest

from ariadne_ltb.application.idempotency import MutationIdempotencyStore


def test_mutation_idempotency_records_action_scoped_result(tmp_path: Path) -> None:
    store = MutationIdempotencyStore(tmp_path)

    store.record_success("assign_ticket", "key-1", {"assignment_id": "a1"})
    record = store.get("assign_ticket", "key-1")

    assert record is not None
    assert record["action"] == "assign_ticket"
    assert record["idempotency_key"] == "key-1"
    assert record["response"]["assignment_id"] == "a1"
    assert store.get("run_assignment", "key-1") is None


def test_mutation_idempotency_rejects_unsafe_keys(tmp_path: Path) -> None:
    store = MutationIdempotencyStore(tmp_path)

    with pytest.raises(ValueError):
        store.record_success("assign_ticket", "../bad", {"assignment_id": "a1"})
