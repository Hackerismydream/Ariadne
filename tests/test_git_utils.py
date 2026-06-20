from __future__ import annotations

from pathlib import Path

from ariadne_ltb.git_utils import changed_files, run_git


def test_changed_files_expands_untracked_directories_to_files(tmp_path: Path) -> None:
    run_git(tmp_path, "init")
    run_git(tmp_path, "config", "user.email", "ariadne@example.test")
    run_git(tmp_path, "config", "user.name", "Ariadne Test")
    (tmp_path / "README.md").write_text("# Target\n", encoding="utf-8")
    run_git(tmp_path, "add", "README.md")
    run_git(tmp_path, "commit", "-m", "init")

    (tmp_path / "mini_code_agent").mkdir()
    (tmp_path / "mini_code_agent" / "cli.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "mini_code_agent" / "__pycache__").mkdir()
    (tmp_path / "mini_code_agent" / "__pycache__" / "cli.cpython-311.pyc").write_bytes(b"cache")

    assert changed_files(tmp_path) == ["mini_code_agent/cli.py"]
