from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Protocol

from ariadne_ltb.git_utils import changed_files, git_diff, git_head, git_status
from ariadne_ltb.models import ExecutionContext, ExecutionResult, FailureReason, stable_id, utc_now
from ariadne_ltb.permissions import validate_changed_files, validate_execution_context_permissions
from ariadne_ltb.secret_safety import validate_secret_safety


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


def _blocked_result(
    context: ExecutionContext,
    backend_name: str,
    reason: str,
    started: str,
    repo: Path,
    command: str | None = None,
    dry_run: bool = False,
    failure_reason: FailureReason = FailureReason.AGENT_ERROR,
) -> ExecutionResult:
    return ExecutionResult(
        id=stable_id("execution", context.ticket_id, backend_name, reason),
        ticket_id=context.ticket_id,
        backend_name=backend_name,
        dry_run=dry_run,
        blocked=True,
        block_reason=reason,
        failure_reason=failure_reason,
        command=command if command is not None else context.command,
        exit_code=2,
        stdout="",
        stderr=reason,
        started_at=started,
        ended_at=utc_now(),
        git_head_before=git_head(repo),
        git_head_after=git_head(repo),
        git_status_before=git_status(repo),
        git_status_after=git_status(repo),
        changed_files=changed_files(repo),
        git_diff=git_diff(repo),
        test_command=context.test_command,
        test_exit_code=None,
        warnings=[reason],
    )


def _permission_block(
    context: ExecutionContext,
    backend_name: str,
    started: str,
    repo: Path,
) -> ExecutionResult | None:
    validation = validate_execution_context_permissions(context)
    if validation.valid:
        secret_validation = validate_secret_safety(
            context.target_repo_path,
            command=context.command,
            allowed_paths=context.allowed_paths,
        )
        if secret_validation.valid:
            return None
        validation = secret_validation
    return _blocked_result(
        context,
        backend_name,
        validation.reason,
        started,
        repo,
        failure_reason=validation.failure_reason or FailureReason.SCOPE_VIOLATION,
    )


def _apply_changed_file_policy(
    result: ExecutionResult,
    context: ExecutionContext,
) -> ExecutionResult:
    validation = validate_changed_files(context.allowed_paths, result.changed_files)
    if validation.valid:
        return result
    warning = validation.reason
    return result.model_copy(
        update={
            "blocked": True,
            "block_reason": warning,
            "failure_reason": validation.failure_reason or FailureReason.SCOPE_VIOLATION,
            "exit_code": result.exit_code if result.exit_code != 0 else 2,
            "warnings": [*result.warnings, warning],
        }
    )


class DryRunBackend:
    name = "dry-run"

    def is_available(self) -> bool:
        return True

    def execute(self, context: ExecutionContext) -> ExecutionResult:
        repo = Path(context.target_repo_path)
        started = utc_now()
        if blocked := _permission_block(context, self.name, started, repo):
            return blocked
        return ExecutionResult(
            id=stable_id("execution", context.ticket_id, self.name, started),
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
        if blocked := _permission_block(context, self.name, started, repo):
            return blocked
        head_before = git_head(repo)
        status_before = git_status(repo)
        validation_reason = self._validate_context(context)
        if validation_reason:
            return _blocked_result(
                context,
                self.name,
                validation_reason,
                started,
                repo,
                failure_reason=FailureReason.SCOPE_VIOLATION,
            )
        cli_path = repo / "demo_todo" / "cli.py"
        test_path = repo / "tests" / "test_cli.py"
        self._add_export_json(cli_path)
        self._add_export_json_test(test_path)
        execution_stdout = json.dumps(
            {
                "backend": self.name,
                "action": "added demo-todo export-json",
                "changed_files": ["demo_todo/cli.py", "tests/test_cli.py"],
                "skill_bundle_path": context.skill_bundle_path,
                "skill_bundle_available": bool(
                    context.skill_bundle_path and Path(context.skill_bundle_path).exists()
                ),
                "provider_skill_dir": context.provider_skill_dir,
                "provider_skill_dir_available": bool(
                    context.provider_skill_dir and Path(context.provider_skill_dir).exists()
                ),
            }
        )
        test_command = context.test_command or f"{self.python_executable} -m pytest"
        test = _run_command(shlex.split(test_command), repo, context.timeout_seconds)
        files = changed_files(repo)
        diff = git_diff(repo)
        return _apply_changed_file_policy(
            ExecutionResult(
                id=stable_id("execution", context.ticket_id, self.name, started),
                ticket_id=context.ticket_id,
                backend_name=self.name,
                dry_run=False,
                blocked=False,
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
            ),
            context,
        )

    def _validate_context(self, context: ExecutionContext) -> str | None:
        task_text = f"{context.handoff_prompt}\n{context.command}".lower()
        if "export-json" not in task_text:
            return "FakeCodexBackend blocked: task or handoff must mention `export-json`."
        required = {"demo_todo/cli.py", "tests/test_cli.py"}
        allowed = set(context.allowed_paths)
        if not required.issubset(allowed):
            missing = ", ".join(sorted(required - allowed))
            return f"FakeCodexBackend blocked: allowed paths missing {missing}."
        return None

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
            return _blocked_result(
                context,
                self.name,
                "ShellBackend requires --confirm-execution.",
                started,
                repo,
                failure_reason=FailureReason.EXTERNAL_EXECUTION_BLOCKED,
            )
        if blocked := _permission_block(context, self.name, started, repo):
            return blocked
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
        return _apply_changed_file_policy(
            ExecutionResult(
                id=stable_id("execution", context.ticket_id, self.name, started),
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
            ),
            context,
        )


class CodexBackend(ShellBackend):
    name = "codex"
    template_env_var = "ARIADNE_CODEX_COMMAND_TEMPLATE"
    default_template = "codex exec --cd {target_repo} - < {handoff_file}"
    executable_name = "codex"
    model_env_var = "ARIADNE_CODEX_MODEL"
    reasoning_effort_env_var = "ARIADNE_CODEX_REASONING_EFFORT"
    service_tier_env_var = "ARIADNE_CODEX_SERVICE_TIER"
    default_service_tier = ""

    def is_available(self) -> bool:
        return shutil.which(self.executable_name) is not None

    def execute(self, context: ExecutionContext) -> ExecutionResult:
        repo = Path(context.target_repo_path)
        started = utc_now()
        handoff_file = self.write_handoff_file(context)
        prepared = context.model_copy(update={"handoff_file": str(handoff_file)})
        command = self.render_command(prepared)
        command_template = self.command_template()
        safe_command = _redact_execution_text(command)
        if os.environ.get("ARIADNE_ENABLE_EXTERNAL_EXECUTION") != "1":
            return _blocked_result(
                prepared,
                self.name,
                "External execution blocked: ARIADNE_ENABLE_EXTERNAL_EXECUTION must be 1.",
                started,
                repo,
                command=safe_command,
                failure_reason=FailureReason.EXTERNAL_EXECUTION_BLOCKED,
            ).model_copy(update=self._evidence_metadata(prepared, command_template))
        if not context.confirm_execution:
            return _blocked_result(
                prepared,
                self.name,
                "External execution blocked: --confirm-execution is required.",
                started,
                repo,
                command=safe_command,
                failure_reason=FailureReason.EXTERNAL_EXECUTION_BLOCKED,
            ).model_copy(update=self._evidence_metadata(prepared, command_template))
        if blocked := _permission_block(prepared, self.name, started, repo):
            return blocked.model_copy(
                update={"command": safe_command, **self._evidence_metadata(prepared, command_template)}
            )
        executable = shlex.split(command)[0] if command.strip() else self.executable_name
        if shutil.which(executable) is None:
            return _blocked_result(
                prepared,
                self.name,
                f"External execution blocked: `{executable}` command is unavailable.",
                started,
                repo,
                command=safe_command,
                failure_reason=FailureReason.COMMAND_UNAVAILABLE,
            ).model_copy(update=self._evidence_metadata(prepared, command_template))

        before_head = git_head(repo)
        before_status = git_status(repo)
        timed_out = False
        try:
            result = subprocess.run(
                command,
                cwd=repo,
                shell=True,
                text=True,
                capture_output=True,
                timeout=context.timeout_seconds,
                check=False,
            )
            exit_code = result.returncode
            stdout = result.stdout
            stderr = result.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            exit_code = 124
            stdout = _timeout_stream(exc.stdout)
            stderr = (
                _timeout_stream(exc.stderr)
                + f"\nCommand timed out after {context.timeout_seconds} seconds."
            ).strip()
        failure_reason, provider_failure_kind, provider_failure_evidence = _classify_provider_failure(
            exit_code,
            stdout,
            stderr,
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
        return _apply_changed_file_policy(
            ExecutionResult(
                id=stable_id("execution", context.ticket_id, self.name, started),
                ticket_id=context.ticket_id,
                backend_name=self.name,
                dry_run=False,
                blocked=False,
                command=safe_command,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                started_at=started,
                ended_at=utc_now(),
                git_head_before=before_head,
                git_head_after=git_head(repo),
                git_status_before=before_status,
                git_status_after=git_status(repo),
                changed_files=changed_files(repo),
                git_diff=git_diff(repo),
                test_command=context.test_command,
                test_exit_code=test.returncode if test else None,
                test_stdout=test.stdout if test else "",
                test_stderr=test.stderr if test else "",
                warnings=["Execution command timed out."] if timed_out else [],
                failure_reason=FailureReason.TIMEOUT if timed_out else failure_reason,
                provider_session_id=_extract_provider_session_id(stdout, stderr),
                provider_failure_kind=provider_failure_kind,
                provider_failure_evidence=provider_failure_evidence,
                **self._evidence_metadata(prepared, command_template),
            ),
            prepared,
        )

    def render_command(self, context: ExecutionContext) -> str:
        template = self.command_template()
        handoff_file = context.handoff_file or str(self._handoff_file_path(context))
        return template.format(
            target_repo=shlex.quote(context.target_repo_path),
            handoff_file=shlex.quote(handoff_file),
            ticket_id=context.ticket_id,
            ticket_key=context.ticket_key or context.ticket_id,
            assignment_id=context.assignment_id or "",
            run_id=context.run_id or "",
            model=_quote_optional(os.environ.get(self.model_env_var, "")),
            reasoning_effort=_quote_optional(os.environ.get(self.reasoning_effort_env_var, "")),
            effort=_quote_optional(os.environ.get(self.reasoning_effort_env_var, "")),
            service_tier=_quote_optional(os.environ.get(self.service_tier_env_var, self.default_service_tier)),
            max_turns=_quote_optional(os.environ.get("ARIADNE_CLAUDE_MAX_TURNS", "")),
            system_prompt=_quote_optional(os.environ.get("ARIADNE_CLAUDE_SYSTEM_PROMPT", "")),
            system_prompt_file=_quote_optional(os.environ.get("ARIADNE_CLAUDE_SYSTEM_PROMPT_FILE", "")),
        )

    def command_template(self) -> str:
        return os.environ.get(self.template_env_var) or self.default_template

    def write_handoff_file(self, context: ExecutionContext) -> Path:
        handoff_file = Path(context.handoff_file) if context.handoff_file else self._handoff_file_path(context)
        handoff_file.parent.mkdir(parents=True, exist_ok=True)
        handoff_file.write_text(context.handoff_prompt, encoding="utf-8")
        return handoff_file

    def _handoff_file_path(self, context: ExecutionContext) -> Path:
        target = Path(context.target_repo_path)
        handoffs_dir = target.parent / "handoffs" if target.parent.name == ".ariadne" else target / ".ariadne" / "handoffs"
        return handoffs_dir / f"{context.ticket_key or context.ticket_id}.md"

    def _evidence_metadata(self, context: ExecutionContext, command_template: str) -> dict[str, str]:
        return {
            "handoff_file": context.handoff_file or str(self._handoff_file_path(context)),
            "command_template": _redact_execution_text(command_template),
            "command_template_env_var": self.template_env_var,
        }


class ClaudeCodeBackend(CodexBackend):
    name = "claude-code"
    template_env_var = "ARIADNE_CLAUDE_COMMAND_TEMPLATE"
    default_template = "claude --print --output-format json < {handoff_file}"
    executable_name = "claude"
    model_env_var = "ARIADNE_CLAUDE_MODEL"
    reasoning_effort_env_var = "ARIADNE_CLAUDE_EFFORT"
    service_tier_env_var = "ARIADNE_CLAUDE_SERVICE_TIER"

    def is_available(self) -> bool:
        return shutil.which(self.executable_name) is not None


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


def _timeout_stream(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _quote_optional(value: str) -> str:
    return shlex.quote(value) if value else ""


def _classify_provider_failure(
    exit_code: int,
    stdout: str,
    stderr: str,
) -> tuple[FailureReason | None, str | None, str | None]:
    if exit_code == 0:
        return None, None, None
    text = f"{stdout}\n{stderr}".lower()
    if any(token in text for token in ["not logged in", "login", "unauthorized", "auth", "api key"]):
        return (
            FailureReason.AUTHENTICATION_FAILED,
            "authentication_failed",
            _provider_failure_evidence(stdout, stderr),
        )
    if any(token in text for token in ["quota", "rate limit", "rate-limit", "usage limit", "billing"]):
        return (
            FailureReason.QUOTA_EXCEEDED,
            "quota_exceeded",
            _provider_failure_evidence(stdout, stderr),
        )
    if any(
        token in text
        for token in ["config.toml", "unknown variant", "invalid config", "unsupported service_tier"]
    ):
        return (
            FailureReason.PROVIDER_CONFIG_INVALID,
            "provider_config_invalid",
            _provider_failure_evidence(stdout, stderr),
        )
    return FailureReason.AGENT_ERROR, "agent_error", _provider_failure_evidence(stdout, stderr)


def _provider_failure_evidence(stdout: str, stderr: str) -> str:
    text = _redact_execution_text((stderr or stdout).strip())
    return text[-1000:]


def _redact_execution_text(text: str) -> str:
    redacted = re.sub(r"sk-[A-Za-z0-9_-]{8,}", "sk-[REDACTED]", text)
    redacted = re.sub(r"(Bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[REDACTED]", redacted)
    redacted = re.sub(
        r"(?i)(api[_-]?key|secret|token|password)=([^\s'\"]+)",
        r"\1=[REDACTED]",
        redacted,
    )
    return redacted


def _extract_provider_session_id(stdout: str, stderr: str) -> str | None:
    for text in [stdout, stderr]:
        parsed = _extract_session_id_from_json(text)
        if parsed:
            return parsed
        match = re.search(r"(?i)\bsession(?:[_ -]?id)?\b\s*[:=]\s*([A-Za-z0-9_.:-]{6,})", text)
        if match:
            return match.group(1)
    return None


def _extract_session_id_from_json(text: str) -> str | None:
    try:
        value = _session_id_from_mapping(json.loads(text))
        if value:
            return value
    except json.JSONDecodeError:
        pass
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        value = _session_id_from_mapping(data)
        if value:
            return value
    return None


def _session_id_from_mapping(data: object) -> str | None:
    if not isinstance(data, dict):
        return None
    for key in ["session_id", "sessionId", "conversation_id", "conversationId"]:
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
    session = data.get("session")
    if isinstance(session, dict):
        value = session.get("id")
        if isinstance(value, str) and value:
            return value
    return None
