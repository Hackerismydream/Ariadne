from __future__ import annotations

from ariadne_ltb.application.repository_scanner import infer_test_commands, scan_repository


def test_repository_scanner_reads_python_and_node_signals(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# Agent\n\nLoop with actions and observations.", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='agent'\n", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"scripts":{"test":"vitest"}}', encoding="utf-8")
    (tmp_path / "agent").mkdir()
    (tmp_path / "agent" / "cli.py").write_text("def main(): pass\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_cli.py").write_text("def test_cli(): assert True\n", encoding="utf-8")

    scan = scan_repository(tmp_path)

    assert "pyproject.toml" in scan.manifests
    assert "package.json" in scan.manifests
    assert "agent/cli.py" in scan.entrypoints
    assert "tests/test_cli.py" in scan.test_paths
    assert "README.md" in scan.selected_files
    assert infer_test_commands(scan.manifests, scan.test_paths) == ["python3.11 -m pytest"]
