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
uv run ari backend diagnose codex
```

Fallback:

```bash
python3.11 -m ariadne_ltb.cli backend doctor
python3.11 -m ariadne_ltb.cli backend diagnose codex
```

The doctor reports backend command availability and environment gate state. It
only prints `set` or `unset` for secrets such as `DEEPSEEK_API_KEY`; it never
prints secret values.

The Codex diagnosis reports whether the local `codex exec --help` advertises
`--prompt-file`, recommends a compatible command template, and checks
`service_tier` without printing secrets.

## Run The Main Codex Demo

`ari demo codex` is the first-class real Codex demo path. Without both safety
gates it records a blocked result through the normal loop. With both gates it
runs through `TicketRunOrchestrator` and `CodexBackend`.

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 \
uv run ari demo codex --confirm-execution --timeout-seconds 180
```

Fallback:

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 \
python3.11 -m ariadne_ltb.cli demo codex --confirm-execution --timeout-seconds 180
```

## Run The Smoke Test

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 \
uv run ari backend smoke-test codex --confirm-execution
```

The current local Codex CLI reads prompts from stdin and does not advertise
`--prompt-file`, so Ariadne's default Codex template is:

```bash
codex exec --cd {target_repo} - < {handoff_file}
```

Some older Codex CLI versions may support `--prompt-file`; `ari backend
diagnose codex` reports the local capability and recommended template.

For a short deterministic smoke task, you can override the template and lower
reasoning effort if your Codex CLI/provider supports that config key:

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 \
ARIADNE_CODEX_COMMAND_TEMPLATE='codex exec -c model_reasoning_effort="none" --cd {target_repo} - < {handoff_file}' \
uv run ari backend smoke-test codex --confirm-execution --timeout-seconds 180
```

Fallback:

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 \
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
- Config error `unknown variant priority`: update `~/.codex/config.toml` so
  `service_tier` is `fast` or another value supported by your account.
- Provider error `Unsupported service_tier: flex`: this account/provider path
  rejected `flex`; use `fast` for the real Codex smoke path.
- Non-zero Codex exit: inspect the execution result, review report, board, and
  target repo diff. Ariadne records the failed run instead of hiding it.

## Result Template

Use `docs/templates/REAL_CODEX_SMOKE_TEST_RESULT.md` to record a real smoke test
result. Do not fill it with success unless the real command actually ran and
produced that result.
