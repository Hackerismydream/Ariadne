# Execution Backend Specification

## Existing issue

`FakeCodexBackend` modifies files through a hard-coded patch. `CodexBackend` / `ClaudeCodeBackend` are thin scaffolds.

## Required behavior

Backends must behave like safe execution adapters.

## ExecutionContext

Must include:

```text
ticket_id
ticket_key if available
build_packet_id
target_repo_path
handoff_prompt
handoff_file
backend_name
allowed_paths
command
test_command
confirm_execution
timeout_seconds
```

## ExecutionResult

Must include:

```text
backend_name
dry_run
blocked
block_reason
command
exit_code
stdout
stderr
started_at
ended_at
git_head_before
git_head_after
git_status_before
git_status_after
changed_files
git_diff
test_command
test_exit_code
test_stdout
test_stderr
warnings
```

If `blocked` field does not exist, add it or represent blocked state clearly.

## FakeCodexBackend

Keep it deterministic, but make it safer.

Required behavior:

- inspect handoff_prompt and/or command;
- only modify files when the task mentions `export-json`;
- verify allowed paths contain `demo_todo/cli.py` and `tests/test_cli.py`;
- if not, return blocked result;
- modify only the demo target project;
- run tests;
- capture git diff and changed files;
- never commit or push.

## CodexBackend

Implement a real adapter scaffold.

Required behavior:

- write handoff prompt to `.ariadne/handoffs/<ticket_key_or_id>.md`;
- read command template from `ARIADNE_CODEX_COMMAND_TEMPLATE`;
- default template:

```text
codex exec --cd {target_repo} --prompt-file {handoff_file}
```

- substitute:

```text
{target_repo}
{handoff_file}
{ticket_id}
{ticket_key}
```

- require:

```text
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1
--confirm-execution
```

- if not enabled, return blocked ExecutionResult;
- if Codex command is unavailable, return blocked ExecutionResult;
- capture stdout/stderr/exit code;
- capture git diff and changed files;
- run tests;
- never commit/push/merge/PR.

Tests must not require Codex installed.

## ClaudeCodeBackend

Same pattern.

Use `ARIADNE_CLAUDE_COMMAND_TEMPLATE`.

Suggested template:

```text
claude --print < {handoff_file}
```

Must be gated by:

```text
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1
--confirm-execution
```

Tests cover disabled path and command rendering only.

## ShellBackend

May remain as a generic low-level backend, but it must require `--confirm-execution`.

Never use ShellBackend as the default full demo path.
