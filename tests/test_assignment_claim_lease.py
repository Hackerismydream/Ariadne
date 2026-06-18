from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.board import export_board
from ariadne_ltb.cli import app
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import AssignmentStatus, StoreInvariantReason
from ariadne_ltb.storage import AriadneStore

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_atomic_claim_prevents_duplicate_assignment_claim(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))

    def claim(runtime_id: str) -> str | None:
        claimed = AriadneStore(tmp_path).claim_next_assignment(runtime_id, lease_seconds=300)
        return claimed.id if claimed else None

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(claim, ["worker-a", "worker-b"]))

    claimed_results = [result for result in results if result is not None]
    updated = store.load_assignment(assignment.id)

    assert claimed_results == [assignment.id]
    assert results.count(assignment.id) == 1
    assert updated.status is AssignmentStatus.CLAIMED
    assert updated.claimed_by_runtime_id in {"worker-a", "worker-b"}
    assert updated.lease_expires_at is not None


def test_stale_assignment_lease_can_be_reclaimed(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    claimed = assignment.mark_claimed("old-worker").model_copy(
        update={"lease_expires_at": "2000-01-01T00:00:00Z"}
    )
    store.save_assignment(claimed)

    reclaimed = store.claim_next_assignment("new-worker", lease_seconds=300)

    assert reclaimed is not None
    assert reclaimed.id == assignment.id
    assert reclaimed.claimed_by_runtime_id == "new-worker"
    assert reclaimed.metadata["lease_reclaimed_from_runtime_id"] == "old-worker"
    assert reclaimed.metadata["lease_reclaimed_from_status"] == "claimed"
    assert reclaimed.metadata["lease_reclaimed_at"]


def test_store_doctor_reports_stale_assignment_lease_as_warning(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    store.save_assignment(
        assignment.mark_claimed("old-worker").model_copy(
            update={"lease_expires_at": "2000-01-01T00:00:00Z"}
        )
    )

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "doctor", "store"])

    assert result.exit_code == 0, result.output
    assert "warnings: 1" in result.output
    assert StoreInvariantReason.STALE_ASSIGNMENT_LEASE.value in result.output


def test_daemon_claim_event_and_board_show_lease_metadata(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    runner = CliRunner()
    assign = runner.invoke(app, ["--root", str(tmp_path), "ticket", "assign", "ARI-003", "--to", "fake-codex"])
    assert assign.exit_code == 0, assign.output

    result = runner.invoke(app, ["--root", str(tmp_path), "daemon", "run-once", "--runtime-id", "lease-worker"])

    ticket = store.resolve_ticket("ARI-003")
    claim_events = [
        event
        for event in store.list_runtime_events_for_ticket(ticket.id)
        if event.stage == "claim" and event.event_type == "claimed"
    ]
    board = export_board(store).read_text(encoding="utf-8")

    assert result.exit_code == 0, result.output
    assert claim_events
    assert claim_events[-1].metadata["claimed_by_runtime_id"] == "lease-worker"
    assert claim_events[-1].metadata["lease_expires_at"]
    assert "Lease expires" in board
    assert "lease-worker" in board
