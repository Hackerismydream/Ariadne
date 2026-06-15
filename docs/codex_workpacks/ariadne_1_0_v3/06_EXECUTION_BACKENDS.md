# 06 — Execution Backends

## Execution safety

Execution must be safe by default.

Rules:

- no auto-commit;
- no auto-push;
- no auto-merge;
- no PR creation;
- no external API writes unless explicitly confirmed;
- target repo path must be explicit;
- backend must record command, stdout, stderr, exit code, duration, and changed files;
- execution writes artifacts to Ariadne workspace, not hidden logs.

## Backend interface

Implement:

```python
class ExecutionBackend(Protocol):
    name: str
    def is_available(self) -> bool: ...
    def execute(self, context: ExecutionContext) -> ExecutionResult: ...
```

## Required backends

### DryRunBackend

No file modifications.

### FakeCodexBackend

Deterministic demo backend that modifies the target project according to the handoff.

For 1.0 demo, it should implement `demo-todo export-json` in `.ariadne/demo_target_project/`.

This backend exists so the full demo passes without external Codex/Claude installations or API keys.

### ShellBackend

Runs a specified local shell command only with explicit confirmation.

Required flag:

```bash
--confirm-execution
```

### Optional CodexBackend

Call installed `codex` CLI only when:

- `codex` is available on PATH;
- user selected `--backend codex`;
- user passed `--confirm-execution`.

The CodexBackend should be configurable by command template, for example:

```text
codex exec --full-auto --cd {target_repo} --prompt-file {handoff_path}
```

If the local Codex CLI uses a different non-interactive syntax, detect availability and document the required command in `docs/development_report.md`. Do not fail tests if Codex CLI is unavailable.

### Optional ClaudeCodeBackend

Scaffold only if time permits.

It should be command-template based, configurable through environment variables, and disabled by default.

## Git capture

Implement utilities:

- `git rev-parse --is-inside-work-tree`
- `git rev-parse HEAD`
- `git status --short`
- `git diff -- .`

For demo target project, initialize git before execution so diff capture works.

## Test execution

ExecutionContext should include test command.

For demo target project:

```bash
python -m pytest
```

or equivalent from target repo.

Capture test stdout/stderr and exit code separately from backend execution if needed.
