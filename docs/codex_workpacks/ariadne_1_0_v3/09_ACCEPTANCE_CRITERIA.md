# 09 — Ariadne 1.0 Acceptance Criteria

## Must pass without external keys

From a clean checkout:

```bash
uv sync --extra dev || true
pytest
ruff check .
python -m ariadne_ltb.cli demo full
python -m ariadne_ltb.cli export board
```

If `python` is unavailable, document equivalent `python3.11` or `uv run python` commands.

## Functional acceptance

1. `ari demo full` ingests at least 3 external source fixtures.
2. It creates at least 3 Build Tickets.
3. Each ticket has a Build Packet or explicit non-build decision.
4. At least one ticket becomes `code_task`.
5. The selected code_task is executed against `.ariadne/demo_target_project/`.
6. Execution captures stdout/stderr/exit code.
7. Execution captures git diff and changed files.
8. Target repo tests run and pass.
9. Reviewer returns pass for successful demo execution.
10. Local memory records are written.
11. Feishu write plan is generated with `dry_run=true`.
12. Board shows full trace.

## Safety acceptance

1. No auto-commit.
2. No auto-push.
3. No auto-merge.
4. No PR creation.
5. No Feishu real write unless `--confirm-write` and credentials exist.
6. No Codex/Claude execution unless backend selected and confirmed.
7. No secrets written to artifacts.

## Code quality acceptance

1. Existing v0.1 commands remain compatible or documented.
2. Tests are deterministic.
3. No test requires external network, Codex, Claude, Feishu, or OpenAI/Anthropic API keys.
4. Type/model boundaries remain clear.
5. Domain objects remain separate: Ticket, Packet, Run, Artifact, ExecutionResult, ReviewReport, MemoryRecord.

## Demo quality acceptance

The generated board and development report should be understandable to a recruiter/interviewer.

They should clearly show:

```text
learning input -> build decision -> coding execution -> review -> memory
```
