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
    assert "integration_doctor" in packet.evidence_refs
    assert "runtime_capabilities" in packet.evidence_refs
    assert "feishu_integrations" in packet.evidence_refs
    assert "github_integrations" in packet.evidence_refs
    assert "product_readiness" in packet.evidence_refs
    assert Path(packet.evidence_refs["integration_doctor"]).exists()
    assert Path(packet.evidence_refs["runtime_capabilities"]).exists()
    assert Path(packet.evidence_refs["product_readiness"]).exists()
    assert packet.product_readiness_status in {"ready", "action_required", "blocked"}
    assert packet.production_acceptance_status in {"ready", "action_required", "blocked"}
    assert packet.run_gate_status in {"ready", "action_required", "blocked"}
    assert "real_codex_execution_evidence" in packet.product_readiness_checks
    assert "real_llm_agent_evidence" in packet.product_readiness_checks
    assert "real_feishu_write_evidence" in packet.product_readiness_checks
    assert "llm_agents" in packet.real_success_evidence
    assert "codex" in packet.real_success_evidence
    assert "github" in packet.real_failure_evidence
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["id"] == packet.id
    assert persisted["evidence_refs"]["integration_doctor"].endswith("integrations.json")
    assert persisted["evidence_refs"]["product_readiness"].endswith("product_readiness.json")
    assert persisted["production_acceptance_status"] in {"ready", "action_required", "blocked"}
    assert persisted["run_gate_status"] in {"ready", "action_required", "blocked"}
    assert "real_github_write_evidence" in persisted["product_readiness_checks"]
    assert "real_llm_agent_evidence" in persisted["product_readiness_checks"]


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
    assert "integration_doctor" in payload["evidence_refs"]
    assert "product_readiness" in payload["evidence_refs"]
    assert payload["production_acceptance_status"] in {"ready", "action_required", "blocked"}
    assert payload["run_gate_status"] in {"ready", "action_required", "blocked"}
    assert "real_codex_execution_evidence" in payload["product_readiness_checks"]
    assert "real_llm_agent_evidence" in payload["product_readiness_checks"]
    assert (tmp_path / ".ariadne" / "doctor" / "integrations.json").exists()
    assert (tmp_path / ".ariadne" / "doctor" / "product_readiness.json").exists()
    assert (tmp_path / ".ariadne" / "evidence" / "release_evidence_packet.json").exists()
