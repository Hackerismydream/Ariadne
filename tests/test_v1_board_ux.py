from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.board_server import board_serve_command
from ariadne_ltb.cli import app
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import GitHubIntegrationResult
from ariadne_ltb.orchestrator import TicketRunOrchestrator
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_board_contains_v1_workbench_sections(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex")

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "export", "board"])
    board = (tmp_path / ".ariadne" / "board" / "index.md").read_text(encoding="utf-8")

    assert result.exit_code == 0, result.output
    for heading in [
        "Ariadne v1.0 Workbench",
        "System Summary",
        "Agent Queue",
        "Tickets by Status",
        "Active Assignments",
        "Daemon / Runtime",
        "Agent Comments",
        "Recent Journal Events",
        "Executed Tickets",
        "Next Tickets",
        "Backend Capability",
        "Safety Gates",
        "Assignment Retry Chain",
        "Agent Handoffs",
        "Codex Gate Status",
        "Execution Permission Profile",
        "Provider Audit Artifacts",
    ]:
        assert heading in board


def test_board_shows_github_status_evidence(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    store.save_github_integration_result(
        GitHubIntegrationResult(
            id="github_link",
            ticket_id=ticket.id,
            ticket_key=ticket.key,
            operation="link",
            ok=True,
            repo="Hackerismydream/Ariadne",
            issue_number=8,
            issue_url="https://github.com/Hackerismydream/Ariadne/issues/8",
        )
    )
    store.save_github_integration_result(
        GitHubIntegrationResult(
            id="github_status",
            ticket_id=ticket.id,
            ticket_key=ticket.key,
            operation="status",
            ok=True,
            repo="Hackerismydream/Ariadne",
            issue_number=8,
            issue_url="https://github.com/Hackerismydream/Ariadne/issues/8",
            pr_number=9,
            pr_url="https://github.com/Hackerismydream/Ariadne/pull/9",
            branch="codex/ariadne-production-frontend-integration",
            commit_sha="abc123",
            evidence={
                "issue": {"number": 8, "state": "OPEN"},
                "pr": {
                    "number": 9,
                    "state": "OPEN",
                    "baseRefName": "main",
                    "headRefName": "codex/ariadne-production-frontend-integration",
                    "mergeable": "MERGEABLE",
                    "reviewDecision": "",
                },
                "checks": [],
                "checks_status": "no_checks_reported",
            },
        )
    )

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "export", "board"])
    board = (tmp_path / ".ariadne" / "board" / "index.md").read_text(encoding="utf-8")

    assert result.exit_code == 0, result.output
    assert "### GitHub Integration" in board
    assert "- PR: `#9`" in board
    assert "- PR base: `main`" in board
    assert "- Mergeable: `MERGEABLE`" in board
    assert "- Review decision: `none`" in board
    assert "- Checks status: `no_checks_reported`" in board
    assert "- Checks summary: pass=`0` pending=`0` fail=`0` total=`0`" in board
    assert "- Recent GitHub operations:" in board


def test_board_counts_completed_failed_github_checks_as_failures(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    store.save_github_integration_result(
        GitHubIntegrationResult(
            id="github_status_with_checks",
            ticket_id=ticket.id,
            ticket_key=ticket.key,
            operation="status",
            ok=True,
            repo="Hackerismydream/Ariadne",
            pr_number=9,
            evidence={
                "pr": {"number": 9, "state": "OPEN", "baseRefName": "main"},
                "checks": [
                    {"name": "unit", "bucket": "pass"},
                    {"name": "lint", "state": "queued"},
                    {"name": "integration", "state": "completed", "conclusion": "failure"},
                ],
                "checks_status": "captured",
            },
        )
    )

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "export", "board"])
    board = (tmp_path / ".ariadne" / "board" / "index.md").read_text(encoding="utf-8")

    assert result.exit_code == 0, result.output
    assert "- Checks summary: pass=`1` pending=`1` fail=`1` total=`3`" in board


def test_board_serve_command_builds_expected_handler(tmp_path: Path) -> None:
    board_dir = tmp_path / ".ariadne" / "board"
    board_dir.mkdir(parents=True)
    (board_dir / "index.html").write_text("<h1>Ariadne</h1>", encoding="utf-8")

    config = board_serve_command(board_dir, port=0, dry_run=True)

    assert config["directory"] == str(board_dir.resolve())
    assert config["port"] == 0


def test_cli_outputs_readable_ticket_state(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    runner = CliRunner()
    assign = runner.invoke(app, ["--root", str(tmp_path), "ticket", "assign", "ARI-003", "--to", "fake-codex"])
    show = runner.invoke(app, ["--root", str(tmp_path), "ticket", "show", "ARI-003"])

    assert assign.exit_code == 0, assign.output
    assert show.exit_code == 0, show.output
    assert "Assignment:" in show.output
    assert "Status:" in show.output
