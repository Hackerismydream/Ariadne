from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app


def test_cli_demo_and_export_board(tmp_path: Path) -> None:
    runner = CliRunner()

    demo_result = runner.invoke(app, ["--root", str(tmp_path), "demo"])
    assert demo_result.exit_code == 0, demo_result.output
    assert "ARI-001" in demo_result.output

    board_result = runner.invoke(app, ["--root", str(tmp_path), "export", "board"])
    assert board_result.exit_code == 0, board_result.output
    assert (tmp_path / ".ariadne" / "board" / "index.md").exists()
