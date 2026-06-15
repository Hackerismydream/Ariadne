# Ariadne True MVP Development Report

## Implemented files

Core product loop:

- `ariadne_ltb/orchestrator.py`
- `ariadne_ltb/planner.py`
- `ariadne_ltb/next_tickets.py`
- `ariadne_ltb/execution.py`
- `ariadne_ltb/review.py`
- `ariadne_ltb/memory.py`
- `ariadne_ltb/board.py`
- `ariadne_ltb/cli.py`
- `ariadne_ltb/full_demo.py`
- `ariadne_ltb/ingest.py`
- `ariadne_ltb/models.py`

Docs, workpack, and tests:

- `README.md`
- `docs/development_report.md`
- `docs/codex_workpacks/ariadne_true_mvp_workpack_v4/`
- `tests/test_true_mvp_product_loop.py`

## What now works

Ariadne now supports the reusable ticket-run full loop:

```bash
ari ingest examples/sources/*.md
ari ticket list
ari ticket run ARI-003 --backend fake-codex
ari export board
```

`ticket run` now performs:

```text
load ticket
  -> plan / update Build Packet
  -> write handoff artifact
  -> execute backend
  -> capture stdout/stderr/exit code
  -> capture git diff and changed files
  -> run tests
  -> review
  -> update ticket status
  -> write memory
  -> generate Feishu dry-run plan
  -> generate next tickets
  -> export board
```

`ari demo full` uses `TicketRunOrchestrator` instead of owning a separate full
chain.

## Feature status

- Reusable `ticket run` full loop: implemented.
- `demo full` through orchestrator: implemented.
- `FakeCodexBackend` validated execution: implemented.
- `CodexBackend` scaffold: implemented, gated by env plus confirmation.
- `ClaudeCodeBackend` scaffold: implemented, gated by env plus confirmation.
- Deterministic planner: implemented.
- Optional LLM planner: implemented with DeepSeek key gating and blocked artifact.
- Memory write-back: implemented.
- Feishu dry-run plan: implemented.
- Generated next Build Tickets: implemented as `next_tickets.json`.
- Board Loop Trace: implemented in `.ariadne/board/index.md`.

## Commands run

```bash
pytest
ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
uv run ari ingest examples/sources/*.md
uv run ari ticket list
uv run ari ticket run ARI-003 --backend fake-codex
uv run ari export board
```

Results:

- `pytest`: passed, 32 tests.
- `ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `uv run ari ingest examples/sources/*.md`: passed.
- `uv run ari ticket list`: passed.
- `uv run ari ticket run ARI-003 --backend fake-codex`: passed.
- `uv run ari export board`: passed.

## Latest local output paths

From the required smoke run in this workspace:

- Board: `.ariadne/board/index.md`
- Memory: `.ariadne/memory/tickets/ticket_91c283a19122.md`
- Feishu dry-run plan: `.ariadne/feishu_plans/feishu_5f3e72f9bd87.json`
- Next tickets: `.ariadne/artifacts/ticket_91c283a19122/next_tickets.json`

These files are runtime outputs under `.ariadne/` and are intentionally
gitignored.

## Stubbed or dry-run behavior

- `FakeCodexBackend` is a deterministic simulator. It validates handoff intent
  and allowed paths before patching the generated demo target project.
- `CodexBackend` writes a handoff file and renders a command template, but real
  execution is blocked unless `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1` and
  `--confirm-execution` are both present.
- `ClaudeCodeBackend` follows the same gated command-template scaffold.
- Feishu write-back is dry-run by default. Real writes require
  `FEISHU_ENABLE_WRITE=1`, `--confirm-write`, credentials, and `lark-cli`.
- LLM planning is optional. Without `DEEPSEEK_API_KEY`, `--planner llm` writes a
  blocked planner artifact and exits gracefully.

## Assumptions made

- The local MVP should default to deterministic planning and `fake-codex` so
  tests do not need network, Codex, Claude, DeepSeek, Feishu, or GitHub tokens.
- The demo target project remains generated under `.ariadne/demo_target_project/`
  and may be rewritten by Ariadne.
- The fixture ingest order is stable so the GitHub README code-task fixture is
  `ARI-003`, matching the required common path.
- Existing low-level commands remain available, but `ticket run` is now the
  product path.

## Known limitations

- No retrieval index over local memory yet.
- No production web UI or FastAPI board.
- Codex and Claude adapters are gated scaffolds, not CI-verified real agent
  integrations.
- Feishu write-back is not production sync; it is a guarded `lark-cli` path.
- The deterministic planner is heuristic and local-first.
- Runtime output under `.ariadne/` is not committed.

## Next recommended Build Tickets

The product now generates next tickets as an artifact after each ticket run. The
latest generated artifact is:

```text
.ariadne/artifacts/ticket_91c283a19122/next_tickets.json
```

Recommended follow-up themes from the generator:

- Add retrieval over local memory.
- Add regression guards for changed target files.
- Reduce reviewer warnings when they appear.
- Expand Feishu dry-run plans into richer docs plus tasks while preserving
  gated real writes.

## ARI-004 Real CodexBackend Smoke Test

Files changed:

- `ariadne_ltb/cli.py`
- `ariadne_ltb/execution.py`
- `tests/test_backend_smoke_cli.py`
- `docs/real_codex_smoke_test.md`
- `docs/templates/REAL_CODEX_SMOKE_TEST_RESULT.md`
- `README.md`
- `docs/development_report.md`

Commands run:

```bash
pytest
ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
uv run ari demo full
uv run ari export board
uv run ari backend doctor
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 \
ARIADNE_CODEX_COMMAND_TEMPLATE='codex exec --cd {target_repo} --prompt-file {handoff_file}' \
uv run ari backend smoke-test codex --confirm-execution
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 \
ARIADNE_CODEX_COMMAND_TEMPLATE='codex exec --ignore-user-config --cd {target_repo} - < {handoff_file}' \
uv run ari backend smoke-test codex --confirm-execution
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 \
ARIADNE_CODEX_COMMAND_TEMPLATE='codex exec -c model_reasoning_effort="none" --cd {target_repo} - < {handoff_file}' \
uv run ari backend smoke-test codex --confirm-execution --timeout-seconds 180
```

Backend doctor result:

```text
FakeCodexBackend: available
ShellBackend: available
CodexBackend command: found /opt/homebrew/bin/codex
ClaudeCodeBackend command: found /opt/homebrew/bin/claude
ARIADNE_ENABLE_EXTERNAL_EXECUTION: unset
ARIADNE_CODEX_COMMAND_TEMPLATE: unset
ARIADNE_CLAUDE_COMMAND_TEMPLATE: unset
FEISHU_ENABLE_WRITE: unset
DEEPSEEK_API_KEY: unset
```

Real Codex command availability:

- `codex`: available at `/opt/homebrew/bin/codex`.

Real smoke test attempts and final result:

- Attempt 1 used the required default-style template
  `codex exec --cd {target_repo} --prompt-file {handoff_file}`.
- Result: Codex exited with code `2`.
- Exact blocker: this local Codex CLI does not support `--prompt-file`:
  `error: unexpected argument '--prompt-file' found`.

- Attempt 2 used a stdin-compatible template:
  `codex exec --ignore-user-config --cd {target_repo} - < {handoff_file}`.
- Result: Codex exited with code `1`.
- Execution result: `.ariadne/execution_results/execution_399c4cb1057e.json`
- Review verdict: `needs_fix`.
- Target project tests still ran and returned `0`.
- Changed files: none.
- Exact blocker: Codex reached the model/provider layer but the local account
  cannot use the configured model:
  `The 'gpt-5.3-codex' model is not supported when using Codex with a ChatGPT account.`

- Local Codex config was then fixed outside the repo:
  `~/.codex/config.toml` changed `service_tier` from `priority` to `fast`.
- The successful smoke-test template was:
  `codex exec -c model_reasoning_effort="none" --cd {target_repo} - < {handoff_file}`.
- Final result: Codex exited with code `0`.
- Execution result: `.ariadne/execution_results/execution_60d17b702878.json`
- Review verdict: `pass`.
- Changed files: `demo_todo/cli.py`, `tests/test_cli.py`.
- Target project tests returned `0`.
- Ariadne captured stdout/stderr, git diff, changed files, tests, review,
  memory, Feishu dry-run plan, next tickets, and board.

Generated output paths from the real smoke-test attempt:

- Board: `.ariadne/board/index.md`
- Memory: `.ariadne/memory/tickets/ticket_91c283a19122.md`
- Feishu dry-run plan: `.ariadne/feishu_plans/feishu_247982ba2e90.json`
- Next tickets: `.ariadne/artifacts/ticket_91c283a19122/next_tickets.json`
- Handoff file: `.ariadne/handoffs/ARI-003.md`

Safety boundaries:

- Real Codex smoke test refuses unless `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1`.
- Real Codex smoke test refuses unless `--confirm-execution` is present.
- Missing Codex command returns a clear blocked CLI result.
- Ariadne does not commit, push, merge, or create PRs during backend execution.
- Runtime outputs remain under `.ariadne/` and are gitignored.

Next recommended Build Ticket:

- ARI-005 - Add automatic Codex CLI compatibility diagnostics for prompt-file
  vs stdin templates, service tier support, reasoning effort, and profile/model
  selection.
