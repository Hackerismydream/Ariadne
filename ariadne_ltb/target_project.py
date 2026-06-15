from __future__ import annotations

import subprocess
import sys
import shutil
from pathlib import Path

from ariadne_ltb.git_utils import git_available, run_git


def ensure_demo_target_project(root: str | Path) -> Path:
    root_path = Path(root).resolve()
    target = root_path / ".ariadne" / "demo_target_project"
    package_dir = target / "demo_todo"
    tests_dir = target / "tests"
    package_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)

    (target / "pyproject.toml").write_text(
        """[project]
name = "demo-todo"
version = "0.1.0"
requires-python = ">=3.11"

[project.scripts]
demo-todo = "demo_todo.cli:main"

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
""",
        encoding="utf-8",
    )
    (target / ".gitignore").write_text(
        "__pycache__/\n*.pyc\n.pytest_cache/\n.demo_todo.json\n",
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text('"""Demo target CLI project."""\n', encoding="utf-8")
    (package_dir / "store.py").write_text(
        """from __future__ import annotations

import json
from pathlib import Path


def store_path() -> Path:
    return Path(".demo_todo.json")


def load_tasks() -> list[str]:
    path = store_path()
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_tasks(tasks: list[str]) -> None:
    store_path().write_text(json.dumps(tasks, indent=2) + "\\n", encoding="utf-8")
""",
        encoding="utf-8",
    )
    (package_dir / "cli.py").write_text(
        """from __future__ import annotations

import argparse

from demo_todo.store import load_tasks, save_tasks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="demo-todo")
    subcommands = parser.add_subparsers(dest="command", required=True)
    add = subcommands.add_parser("add")
    add.add_argument("task")
    subcommands.add_parser("list")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "add":
        tasks = load_tasks()
        tasks.append(args.task)
        save_tasks(tasks)
        print(f"added: {args.task}")
        return 0
    if args.command == "list":
        for task in load_tasks():
            print(task)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
""",
        encoding="utf-8",
    )
    (tests_dir / "test_cli.py").write_text(
        f"""from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    return subprocess.run(
        [sys.executable, "-m", "demo_todo.cli", *args],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def test_add_and_list_task(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    add = run_cli("add", "write tests")
    assert add.returncode == 0
    listed = run_cli("list")
    assert listed.returncode == 0
    assert "write tests" in listed.stdout


def test_python_executable_available() -> None:
    assert {sys.executable!r}
""",
        encoding="utf-8",
    )
    if git_available() and not (target / ".git").exists():
        run_git(target, "init")
        run_git(target, "add", ".")
        subprocess.run(
            [
                "git",
                "-c",
                "user.email=ariadne@example.invalid",
                "-c",
                "user.name=Ariadne Demo",
                "commit",
                "-m",
                "Initial demo target project",
            ],
            cwd=target,
            text=True,
            capture_output=True,
            check=False,
        )
    return target


def target_test_command() -> str:
    pytest_bin = shutil.which("pytest")
    if pytest_bin:
        return pytest_bin
    return f"{sys.executable} -m pytest"
