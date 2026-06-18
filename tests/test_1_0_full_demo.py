from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.execution import ExecutionContext, FakeCodexBackend, ShellBackend
from ariadne_ltb.full_demo import run_full_demo
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import ArtifactType, BuildDecision, LandingEvidence, ReviewVerdict, SourceType, TicketStatus
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))
SOURCE_FIXTURE_COUNT = len(SOURCE_FIXTURES)


def test_ingest_multiple_sources_creates_unique_tickets_and_packets(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    tickets = ingest_sources(store, SOURCE_FIXTURES)

    assert len(tickets) == SOURCE_FIXTURE_COUNT
    assert [ticket.key for ticket in tickets] == [
        f"ARI-{index:03d}" for index in range(1, SOURCE_FIXTURE_COUNT + 1)
    ]
    assert {
        SourceType.PAPER.value,
        SourceType.BLOG.value,
        SourceType.GITHUB_REPO.value,
    }.issubset({ticket.source_type for ticket in tickets})
    assert all(ticket.build_packet_id for ticket in tickets)

    packets = [store.load_build_packet(ticket.build_packet_id) for ticket in tickets if ticket.build_packet_id]
    assert any(packet.build_decision is BuildDecision.CODE_TASK for packet in packets)
    assert all(packet.evidence for packet in packets)
    assert all(packet.acceptance_criteria for packet in packets)


def test_demo_target_project_starts_without_export_json(tmp_path: Path) -> None:
    target = ensure_demo_target_project(tmp_path)

    assert (target / "demo_todo" / "cli.py").exists()
    assert "export-json" not in (target / "demo_todo" / "cli.py").read_text(encoding="utf-8")
    assert (target / ".git").exists()


def test_fake_codex_backend_modifies_target_and_captures_diff_and_tests(tmp_path: Path) -> None:
    target = ensure_demo_target_project(tmp_path)
    backend = FakeCodexBackend()
    result = backend.execute(
        ExecutionContext(
            ticket_id="ticket_demo",
            build_packet_id="packet_demo",
            target_repo_path=str(target),
            handoff_prompt="Add demo-todo export-json support.",
            backend_name="fake-codex",
            allowed_paths=["demo_todo/cli.py", "tests/test_cli.py"],
            command="add export-json",
            test_command=f"{backend.python_executable} -m pytest",
            confirm_execution=False,
            timeout_seconds=30,
        )
    )

    assert result.exit_code == 0
    assert result.test_exit_code == 0
    assert sorted(result.changed_files) == ["demo_todo/cli.py", "tests/test_cli.py"]
    assert "export-json" in result.git_diff
    assert json.loads(result.stdout)["backend"] == "fake-codex"


def test_shell_backend_requires_confirmation(tmp_path: Path) -> None:
    target = ensure_demo_target_project(tmp_path)
    result = ShellBackend().execute(
        ExecutionContext(
            ticket_id="ticket_demo",
            build_packet_id="packet_demo",
            target_repo_path=str(target),
            handoff_prompt="No-op",
            backend_name="shell",
            allowed_paths=["."],
            command="python -c 'print(123)'",
            test_command="",
            confirm_execution=False,
            timeout_seconds=30,
        )
    )

    assert result.exit_code != 0
    assert "requires --confirm-execution" in result.stderr


def test_full_demo_runs_complete_learning_to_build_chain(tmp_path: Path) -> None:
    result = run_full_demo(root=tmp_path, source_paths=SOURCE_FIXTURES)
    store = AriadneStore(tmp_path)

    assert result.sources_ingested == SOURCE_FIXTURE_COUNT
    assert result.tickets_created == SOURCE_FIXTURE_COUNT
    assert result.backend_name == "fake-codex"
    assert result.review_verdict is ReviewVerdict.PASS
    assert result.test_exit_code == 0
    assert result.changed_files == ["demo_todo/cli.py", "tests/test_cli.py"]
    assert result.board_path.exists()
    assert result.board_html_path.exists()
    assert result.memory_path.exists()
    assert result.feishu_plan_path.exists()

    selected = store.load_ticket(result.selected_ticket_id)
    assert selected.status is TicketStatus.DONE
    assert selected.metadata["execution_result_id"] == result.execution_result_id

    artifacts = [store.load_artifact(artifact_id) for artifact_id in selected.artifact_ids]
    assert ArtifactType.EXECUTION_LOG in {artifact.artifact_type for artifact in artifacts}
    assert ArtifactType.GIT_DIFF in {artifact.artifact_type for artifact in artifacts}
    assert ArtifactType.TEST_OUTPUT in {artifact.artifact_type for artifact in artifacts}
    assert ArtifactType.LANDING_EVIDENCE in {artifact.artifact_type for artifact in artifacts}

    board = result.board_path.read_text(encoding="utf-8")
    assert "learning input -> build decision -> coding execution -> review -> memory" in board
    assert "Landing Evidence" in board
    assert "fake-codex" in board
    assert "demo_todo/cli.py" in board


def test_full_demo_writes_valid_landing_evidence_packet(tmp_path: Path) -> None:
    result = run_full_demo(root=tmp_path, source_paths=SOURCE_FIXTURES)
    store = AriadneStore(tmp_path)
    ticket = store.load_ticket(result.selected_ticket_id)

    json_path = Path(ticket.metadata["landing_evidence_json_path"])
    md_path = Path(ticket.metadata["landing_evidence_md_path"])
    evidence = LandingEvidence.model_validate_json(json_path.read_text(encoding="utf-8"))

    assert json_path.name == "landing_evidence.json"
    assert md_path.name == "landing_evidence.md"
    assert md_path.exists()
    assert evidence.ticket_key == result.selected_ticket_key
    assert evidence.backend_name == "fake-codex"
    assert evidence.changed_files == ["demo_todo/cli.py", "tests/test_cli.py"]
    assert evidence.git_diff_summary["raw_diff_embedded"] is False
    assert evidence.git_diff_summary["additions"] > 0
    assert evidence.test_results[0].command
    assert evidence.test_results[0].status == "passed"
    assert evidence.review_verdict is ReviewVerdict.PASS
    assert evidence.memory_path == str(result.memory_path)
    assert evidence.board_path == str(result.board_path)
    assert evidence.next_tickets_path == str(result.next_tickets_path)
    assert evidence.gate_inputs["external_execution_enabled"] is False
    assert any(artifact.kind == "git_diff" for artifact in evidence.linked_artifacts)
    assert any(artifact.kind == "execution_log" for artifact in evidence.linked_artifacts)


def test_blocked_full_demo_still_writes_partial_landing_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", raising=False)

    result = run_full_demo(root=tmp_path, source_paths=SOURCE_FIXTURES, backend_name="codex")
    store = AriadneStore(tmp_path)
    ticket = store.load_ticket(result.selected_ticket_id)
    evidence = LandingEvidence.model_validate_json(
        Path(ticket.metadata["landing_evidence_json_path"]).read_text(encoding="utf-8")
    )

    assert evidence.backend_name == "codex"
    assert evidence.partial is True
    assert evidence.gate_inputs["blocked"] is True
    assert evidence.gate_inputs["failure_reason"] == "external_execution_blocked"
    assert evidence.review_verdict is ReviewVerdict.BLOCKED
    assert Path(evidence.board_path).exists()


def test_cli_ingest_ticket_list_and_full_demo(tmp_path: Path) -> None:
    runner = CliRunner()

    ingest_result = runner.invoke(
        app,
        ["--root", str(tmp_path), "ingest", *[str(path) for path in SOURCE_FIXTURES]],
    )
    assert ingest_result.exit_code == 0, ingest_result.output
    assert f"Ingested {SOURCE_FIXTURE_COUNT} source" in ingest_result.output

    list_result = runner.invoke(app, ["--root", str(tmp_path), "ticket", "list"])
    assert list_result.exit_code == 0, list_result.output
    assert "ARI-003" in list_result.output

    demo_result = runner.invoke(app, ["--root", str(tmp_path), "demo", "full"])
    assert demo_result.exit_code == 0, demo_result.output
    assert f"sources ingested: {SOURCE_FIXTURE_COUNT}" in demo_result.output
    assert "reviewer verdict: pass" in demo_result.output
    assert (tmp_path / ".ariadne" / "board" / "index.md").exists()
