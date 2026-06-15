# Real CodexBackend Smoke Test

This smoke test proves that Ariadne can orchestrate a real local Codex CLI run
through the same ticket loop used by the default MVP path:

```text
source fixtures
  -> Build Tickets
  -> Build Packet + handoff
  -> CodexBackend
  -> stdout/stderr/exit code
  -> git diff + changed files
  -> tests
  -> review
  -> memory + Feishu dry-run + next tickets + board
```

The default demo still uses `FakeCodexBackend`. Real Codex execution is optional,
local, safety-gated, and never auto-commits.

## Safety Gates

Real Codex execution requires both:

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1
--confirm-execution
```

If either gate is missing, Ariadne refuses before creating the demo target
project for the smoke test. The runtime still never commits, pushes, merges, or
creates PRs.

## Doctor

Run backend diagnostics first:

```bash
uv run ari backend doctor
```

Fallback:

```bash
python3.11 -m ariadne_ltb.cli backend doctor
```

The doctor reports backend command availability and environment gate state. It
only prints `set` or `unset` for secrets such as `DEEPSEEK_API_KEY`; it never
prints secret values.

## Run The Smoke Test

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 \
ARIADNE_CODEX_COMMAND_TEMPLATE='codex exec --cd {target_repo} --prompt-file {handoff_file}' \
uv run ari backend smoke-test codex --confirm-execution
```

Some Codex CLI versions do not support `--prompt-file` and instead read prompts
from stdin. For those versions, use:

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 \
ARIADNE_CODEX_COMMAND_TEMPLATE='codex exec --cd {target_repo} - < {handoff_file}' \
uv run ari backend smoke-test codex --confirm-execution
```

Fallback:

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 \
ARIADNE_CODEX_COMMAND_TEMPLATE='codex exec --cd {target_repo} --prompt-file {handoff_file}' \
python3.11 -m ariadne_ltb.cli backend smoke-test codex --confirm-execution
```

The command uses `TicketRunOrchestrator`; it does not duplicate the product
pipeline.

## Inspect Outputs

After a run, inspect:

```bash
uv run ari export board
```

Key outputs:

- `.ariadne/board/index.md`
- `.ariadne/memory/tickets/<ticket_id>.md`
- `.ariadne/feishu_plans/<plan_id>.json`
- `.ariadne/artifacts/<ticket_id>/next_tickets.json`
- `.ariadne/handoffs/<ticket_key>.md`

## Interpreting Blocked Results

- `ARIADNE_ENABLE_EXTERNAL_EXECUTION` unset: set it to `1` for real execution.
- Missing `--confirm-execution`: pass the flag explicitly.
- Codex command missing: install or authenticate Codex CLI, then rerun
  `ari backend doctor`.
- Non-zero Codex exit: inspect the execution result, review report, board, and
  target repo diff. Ariadne records the failed run instead of hiding it.

## Result Template

Use `docs/templates/REAL_CODEX_SMOKE_TEST_RESULT.md` to record a real smoke test
result. Do not fill it with success unless the real command actually ran and
produced that result.
