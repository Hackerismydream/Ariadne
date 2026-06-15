from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Protocol

from ariadne_ltb.git_utils import changed_files, git_diff, git_head, git_status
from ariadne_ltb.models import ExecutionContext, ExecutionResult, stable_id, utc_now


class ExecutionBackend(Protocol):
    name: str

    def is_available(self) -> bool:
        ...

    def execute(self, context: ExecutionContext) -> ExecutionResult:
        ...


def _run_command(command: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )


class DryRunBackend:
    name = "dry-run"

    def is_available(self) -> bool:
        return True

    def execute(self, context: ExecutionContext) -> ExecutionResult:
        repo = Path(context.target_repo_path)
        started = utc_now()
        return ExecutionResult(
            id=stable_id("execution", context.ticket_id, self.name),
            ticket_id=context.ticket_id,
            backend_name=self.name,
            dry_run=True,
            command=context.command,
            exit_code=0,
            stdout="Dry run only; no target files changed.",
            stderr="",
            started_at=started,
            ended_at=utc_now(),
            git_head_before=git_head(repo),
            git_head_after=git_head(repo),
            git_status_before=git_status(repo),
            git_status_after=git_status(repo),
            changed_files=[],
            git_diff="",
            test_command=context.test_command,
            test_exit_code=None,
        )


class FakeCodexBackend:
    name = "fake-codex"
    python_executable = sys.executable

    def is_available(self) -> bool:
        return True

    def execute(self, context: ExecutionContext) -> ExecutionResult:
        repo = Path(context.target_repo_path)
        started = utc_now()
        head_before = git_head(repo)
        status_before = git_status(repo)
        cli_path = repo / "demo_todo" / "cli.py"
        test_path = repo / "tests" / "test_cli.py"
        self._add_export_json(cli_path)
        self._add_export_json_test(test_path)
        execution_stdout = json.dumps(
            {
                "backend": self.name,
                "action": "added demo-todo export-json",
                "changed_files": ["demo_todo/cli.py", "tests/test_cli.py"],
            }
        )
        test_command = context.test_command or f"{self.python_executable} -m pytest"
        test = _run_command(shlex.split(test_command), repo, context.timeout_seconds)
        files = changed_files(repo)
        diff = git_diff(repo)
        return ExecutionResult(
            id=stable_id("execution", context.ticket_id, self.name),
            ticket_id=context.ticket_id,
            backend_name=self.name,
            dry_run=False,
            command=context.command,
            exit_code=0,
            stdout=execution_stdout,
            stderr="",
            started_at=started,
            ended_at=utc_now(),
            git_head_before=head_before,
            git_head_after=git_head(repo),
            git_status_before=status_before,
            git_status_after=git_status(repo),
            changed_files=files,
            git_diff=diff,
            test_command=test_command,
            test_exit_code=test.returncode,
            test_stdout=test.stdout,
            test_stderr=test.stderr,
            warnings=[] if diff else ["git diff unavailable or empty"],
        )

    def _add_export_json(self, cli_path: Path) -> None:
        text = cli_path.read_text(encoding="utf-8")
        if "export-json" in text:
            return
        text = text.replace("import argparse\n", "import argparse\nimport json\n")
        text = text.replace(
            '    subcommands.add_parser("list")\n',
            '    subcommands.add_parser("list")\n    subcommands.add_parser("export-json")\n',
        )
        text = text.replace(
            '    if args.command == "list":\n        for task in load_tasks():\n            print(task)\n        return 0\n',
            '    if args.command == "list":\n        for task in load_tasks():\n            print(task)\n        return 0\n    if args.command == "export-json":\n        print(json.dumps(load_tasks()))\n        return 0\n',
        )
        cli_path.write_text(text, encoding="utf-8")

    def _add_export_json_test(self, test_path: Path) -> None:
        text = test_path.read_text(encoding="utf-8")
        if "test_export_json" in text:
            return
        text += '''

def test_export_json_outputs_valid_json(tmp_path, monkeypatch) -> None:
    import json

    monkeypatch.chdir(tmp_path)
    assert run_cli("add", "ship demo").returncode == 0
    exported = run_cli("export-json")
    assert exported.returncode == 0
    assert json.loads(exported.stdout) == ["ship demo"]
'''
        test_path.write_text(text, encoding="utf-8")


class ShellBackend:
    name = "shell"

    def is_available(self) -> bool:
        return True

    def execute(self, context: ExecutionContext) -> ExecutionResult:
        repo = Path(context.target_repo_path)
        started = utc_now()
        if not context.confirm_execution:
            return ExecutionResult(
                id=stable_id("execution", context.ticket_id, self.name),
                ticket_id=context.ticket_id,
                backend_name=self.name,
                dry_run=False,
                command=context.command,
                exit_code=2,
                stdout="",
                stderr="ShellBackend requires --confirm-execution.",
                started_at=started,
                ended_at=utc_now(),
                git_head_before=git_head(repo),
                git_head_after=git_head(repo),
                git_status_before=git_status(repo),
                git_status_after=git_status(repo),
            )
        result = subprocess.run(
            context.command,
            cwd=repo,
            shell=True,
            text=True,
            capture_output=True,
            timeout=context.timeout_seconds,
            check=False,
        )
        test = None
        if context.test_command:
            test = subprocess.run(
                context.test_command,
                cwd=repo,
                shell=True,
                text=True,
                capture_output=True,
                timeout=context.timeout_seconds,
                check=False,
            )
        return ExecutionResult(
            id=stable_id("execution", context.ticket_id, self.name),
            ticket_id=context.ticket_id,
            backend_name=self.name,
            dry_run=False,
            command=context.command,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            started_at=started,
            ended_at=utc_now(),
            git_status_before="",
            git_status_after=git_status(repo),
            changed_files=changed_files(repo),
            git_diff=git_diff(repo),
            test_command=context.test_command,
            test_exit_code=test.returncode if test else None,
            test_stdout=test.stdout if test else "",
            test_stderr=test.stderr if test else "",
        )


class CodexBackend(ShellBackend):
    name = "codex"

    def is_available(self) -> bool:
        return shutil.which("codex") is not None

    def execute(self, context: ExecutionContext) -> ExecutionResult:
        if os.environ.get("ARIADNE_ENABLE_EXTERNAL_EXECUTION") != "1":
            blocked = context.model_copy(
                update={
                    "command": "codex backend refused: ARIADNE_ENABLE_EXTERNAL_EXECUTION != 1",
                    "confirm_execution": False,
                }
            )
            return super().execute(blocked)
        return super().execute(context)


class ClaudeCodeBackend(CodexBackend):
    name = "claude-code"

    def is_available(self) -> bool:
        return shutil.which("claude") is not None


def backend_for_name(name: str) -> ExecutionBackend:
    backends: dict[str, ExecutionBackend] = {
        "dry-run": DryRunBackend(),
        "fake-codex": FakeCodexBackend(),
        "shell": ShellBackend(),
        "codex": CodexBackend(),
        "claude-code": ClaudeCodeBackend(),
    }
    if name not in backends:
        msg = f"unknown backend: {name}"
        raise ValueError(msg)
    return backends[name]
