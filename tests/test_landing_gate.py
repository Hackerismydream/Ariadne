from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.orchestrator import TicketRunOrchestrator
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_cli_landing_gate_reports_ready_after_ticket_run(tmp_path: Path) -> None:
    runner = CliRunner()
    ingest_result = runner.invoke(
        app,
        ["--root", str(tmp_path), "ingest", *[str(path) for path in SOURCE_FIXTURES]],
    )
    assert ingest_result.exit_code == 0, ingest_result.output

    run_result = runner.invoke(app, ["--root", str(tmp_path), "ticket", "run", "ARI-003", "--backend", "fake-codex"])
    assert run_result.exit_code == 0, run_result.output

    gate_result = runner.invoke(
        app,
        ["--root", str(tmp_path), "landing", "gate", "ARI-003", "--output", "json", "--require-ready"],
    )
    payload = json.loads(gate_result.output)

    assert gate_result.exit_code == 0, gate_result.output
    assert payload["ticket_key"] == "ARI-003"
    assert payload["status"] == "ready"
    assert payload["landing_evidence_path"].endswith("landing_evidence.json")
    assert payload["report_path"].endswith("landing_gate_report.json")
    assert Path(payload["report_path"]).exists()
    assert all(check["status"] == "pass" for check in payload["checks"])


def test_cli_landing_gate_blocks_without_landing_evidence(tmp_path: Path) -> None:
    runner = CliRunner()
    ingest_sources_path = [str(path) for path in SOURCE_FIXTURES]
    ingest_result = runner.invoke(app, ["--root", str(tmp_path), "ingest", *ingest_sources_path])
    assert ingest_result.exit_code == 0, ingest_result.output

    gate_result = runner.invoke(
        app,
        ["--root", str(tmp_path), "landing", "gate", "ARI-003", "--output", "json", "--require-ready"],
    )
    payload = json.loads(gate_result.output)

    assert gate_result.exit_code == 2, gate_result.output
    assert payload["ticket_key"] == "ARI-003"
    assert payload["status"] == "blocked"
    assert payload["blockers"] == ["Landing evidence JSON artifact is missing or invalid."]
    assert payload["report_path"].endswith("landing_gate_report.json")
    assert Path(payload["report_path"]).exists()


def test_landing_gate_table_output(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex")

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "landing", "gate", "ARI-003"])

    assert result.exit_code == 0, result.output
    assert "ticket: ARI-003" in result.output
    assert "landing gate: ready" in result.output
    assert "landing_evidence_complete\tpass\tLanding evidence is complete." in result.output
