from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_cli_demo_and_export_board(tmp_path: Path) -> None:
    runner = CliRunner()

    demo_result = runner.invoke(app, ["--root", str(tmp_path), "demo"])
    assert demo_result.exit_code == 0, demo_result.output
    assert "ARI-001" in demo_result.output

    board_result = runner.invoke(app, ["--root", str(tmp_path), "export", "board"])
    assert board_result.exit_code == 0, board_result.output
    assert (tmp_path / ".ariadne" / "board" / "index.md").exists()


def test_cli_ingest_planner_reports_per_ticket_progress(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "ingest",
            str(SOURCE_FIXTURES[0]),
            "--planner",
            "deterministic",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "planning ARI-001 with deterministic..." in result.output
    assert "planned ARI-001: packet" in result.output
    assert "handoff:" in result.output
    assert "Ingested 1 source(s)" in result.output


def test_cli_ingest_llm_planner_reports_blocked_artifact_when_key_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    result = CliRunner().invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "ingest",
            str(SOURCE_FIXTURES[0]),
            "--planner",
            "llm",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "planning ARI-001 with llm..." in result.output
    assert "planner blocked for ARI-001: DEEPSEEK_API_KEY is required for --planner llm." in result.output
    assert "planner error artifact:" in result.output
    assert "Ingested 1 source(s)" in result.output
