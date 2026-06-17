from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.evidence import generate_release_evidence_packet
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.orchestrator import TicketRunOrchestrator
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_release_evidence_packet_records_current_store_and_board(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex")

    packet, path = generate_release_evidence_packet(store)

    assert path.exists()
    assert packet.ticket_count >= 4
    assert packet.execution_result_count >= 1
    assert packet.review_report_count >= 1
    assert packet.board_path
    assert Path(packet.board_path).exists()
    assert packet.store_invariants_ok is True
    assert "board" in packet.evidence_refs
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["id"] == packet.id


def test_evidence_packet_cli_writes_machine_readable_json(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex")

    result = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "evidence", "packet", "--output", "json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ticket_count"] >= 4
    assert payload["execution_result_count"] >= 1
    assert payload["review_report_count"] >= 1
    assert (tmp_path / ".ariadne" / "evidence" / "release_evidence_packet.json").exists()
