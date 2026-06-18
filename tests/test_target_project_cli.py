from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project


def test_target_project_cli_register_persists_project_resource(tmp_path: Path) -> None:
    target = ensure_demo_target_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "target-project",
            "register",
            str(target),
            "--id",
            "local-default",
            "--label",
            "Local Default",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "target project: local-default" in result.output
    resources = AriadneStore(tmp_path).load_project_resources()
    assert resources[0].id == "local-default"
    assert resources[0].resource_ref["local_path"] == str(target)


def test_target_project_cli_list_redacts_path(tmp_path: Path) -> None:
    target = ensure_demo_target_project(tmp_path)
    runner = CliRunner()
    runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "target-project",
            "register",
            str(target),
            "--id",
            "local-default",
            "--label",
            "Local Default",
        ],
    )

    result = runner.invoke(app, ["--root", str(tmp_path), "target-project", "list"])

    assert result.exit_code == 0, result.output
    assert "local-default" in result.output
    assert "Local Default" in result.output
    assert str(target) not in result.output
