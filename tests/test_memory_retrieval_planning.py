from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.board import export_board
from ariadne_ltb.cli import app
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.memory import search_memory
from ariadne_ltb.models import MemoryRecord
from ariadne_ltb.planner import DeterministicPlanner
from ariadne_ltb.storage import AriadneStore


def test_memory_search_returns_relevant_local_snippets(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    store.save_memory_record(
        MemoryRecord(
            id="memory_ticket_alpha",
            ticket_id="ticket_alpha",
            title="ARI-001 - Planner memory retrieval",
            decision_log_entry="ARI-001: planner should cite prior review memory.",
            build_summary="Implemented deterministic memory search before planning.",
            review_summary="Reviewer passed memory retrieval evidence checks.",
            source_refs=["examples/sources/memory.md"],
            artifact_refs=["review_report_alpha", "next_tickets_alpha"],
            next_actions=["Use memory search results as BuildPacket evidence."],
        )
    )
    store.save_memory_record(
        MemoryRecord(
            id="memory_ticket_beta",
            ticket_id="ticket_beta",
            title="ARI-002 - Feishu dry-run",
            decision_log_entry="ARI-002: Feishu remains dry-run.",
            build_summary="No planner retrieval work.",
            review_summary="Reviewer passed dry-run checks.",
        )
    )

    hits = search_memory(store, "planner memory retrieval evidence", limit=3)

    assert hits
    assert hits[0].ticket_id == "ticket_alpha"
    assert "memory" in hits[0].snippet
    assert "retrieval" in hits[0].snippet
    assert hits[0].source_ref.endswith(".ariadne/memory/tickets/ticket_alpha.json")
    assert "review_report_alpha" in hits[0].artifact_refs


def test_memory_search_cli_outputs_json_without_network(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    store.save_memory_record(
        MemoryRecord(
            id="memory_ticket_alpha",
            ticket_id="ticket_alpha",
            title="ARI-001 - Planner memory retrieval",
            decision_log_entry="ARI-001: planner should cite prior review memory.",
            build_summary="Implemented deterministic memory search before planning.",
            review_summary="Reviewer passed memory retrieval evidence checks.",
        )
    )

    result = CliRunner().invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "memory",
            "search",
            "planner memory retrieval",
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload[0]["ticket_id"] == "ticket_alpha"
    assert payload[0]["source_ref"].endswith(".ariadne/memory/tickets/ticket_alpha.json")


def test_planner_use_memory_cites_memory_in_packet_handoff_and_board(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    store.save_memory_record(
        MemoryRecord(
            id="memory_ticket_prior",
            ticket_id="ticket_prior",
            title="ARI-010 - Memory search planning",
            decision_log_entry="ARI-010: use memory retrieval before planner handoff.",
            build_summary="Memory search produced prior review evidence for future planning.",
            review_summary="Reviewer passed memory evidence checks.",
            artifact_refs=["review_report_prior", "next_tickets_prior"],
        )
    )
    source = tmp_path / "memory_feature.md"
    source.write_text(
        "# Planner Memory Feature\n\n"
        "Implementation note: add memory retrieval evidence to planner handoff.\n",
        encoding="utf-8",
    )
    ticket = ingest_sources(store, [source])[0]

    result = DeterministicPlanner(use_memory=True).plan_ticket(store, ticket)
    packet = store.load_build_packet(result.build_packet_id)
    handoff = Path(result.handoff_artifact_path).read_text(encoding="utf-8")
    board = export_board(store).read_text(encoding="utf-8")

    assert packet.metadata["memory_search_enabled"] is True
    assert packet.metadata["memory_evidence_count"] >= 1
    assert packet.metadata["memory_hits"][0]["source_ref"].endswith(
        ".ariadne/memory/tickets/ticket_prior.json"
    )
    assert any(item.location == "memory:ticket_prior" for item in packet.evidence)
    assert "## Memory Context" in handoff
    assert "ticket_prior.json" in handoff
    assert "### Planner Memory Evidence" in board
    assert "ticket_prior.json" in board
