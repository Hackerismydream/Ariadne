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

## ARI-005 Multica Architecture Alignment

Multica files/docs inspected:

- `README.md`
- `CLI_AND_DAEMON.md`
- `SELF_HOSTING.md`
- `CONTRIBUTING.md`
- `apps/docs/content/docs/agents.mdx`
- `apps/docs/content/docs/tasks.mdx`
- `apps/docs/content/docs/squads.mdx`
- `apps/docs/content/docs/skills.mdx`
- `apps/docs/content/docs/project-resources.mdx`
- `apps/docs/content/docs/daemon-runtimes.mdx`
- `apps/docs/content/docs/assigning-issues.mdx`
- `apps/docs/content/docs/mentioning-agents.mdx`
- `apps/docs/content/docs/providers.mdx`
- `server/pkg/db/queries/agent.sql`
- `server/pkg/db/queries/project_resource.sql`
- `server/pkg/db/queries/runtime.sql`
- `server/pkg/protocol/events.go`
- `server/pkg/taskfailure/failure.go`
- `server/pkg/taskfailure/classify.go`
- `server/internal/daemon/daemon.go`
- `server/cmd/server/runtime_sweeper.go`
- `packages/core/types/project.ts`
- `packages/core/types/events.ts`

Architecture docs created:

- `docs/architecture/multica_architecture_digest.md`
- `docs/architecture/ariadne_multica_gap_report.md`
- `docs/adr/ADR-0002-multica-architecture-alignment.md`
- `docs/smoke_test_results/ARI-004-real-codex-summary.md`

Code changes implemented:

- Added `AgentRun.lifecycle_state` compatible with created/running/terminal.
- Added typed `FailureReason` and persisted it on runs, execution results, and
  review reports.
- Added `RuntimeCapability` snapshots and persisted backend doctor output to
  `.ariadne/runtimes/capability_snapshot.json`.
- Added `ProjectResource` serialization under `.ariadne/project/resources.json`.
- Added target repo path validation and local directory locking under
  `.ariadne/locks/`.
- Added default BuildSkill packs under `.skills/`.
- Added handoff skill references.
- Added `route_decision.json` artifacts.
- Added progress events for route, execution, review, memory, next tickets, and
  board export.
- Extended the static board with runtime capability, route decision, project
  resources, BuildSkill, and progress-event sections.

Key Multica takeaways applied:

- Keep the work carrier and execution run separate.
- Make runtime capability visible before execution.
- Treat project context as typed resources, not unstructured prompt text.
- Serialize local-directory execution by resolved path.
- Use typed failure reasons instead of only free-form stderr.
- Make route decisions and progress events first-class artifacts.

Deliberately deferred:

- Full daemon queue with claim/heartbeat/retry.
- WebSocket progress streaming.
- PostgreSQL persistence.
- Provider-specific skill materialization.
- Session resume and automatic retry.
- Web UI polish.

Safety boundaries:

- Real Codex execution remains gated by `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1`
  and `--confirm-execution`.
- Real Feishu writes remain gated by `FEISHU_ENABLE_WRITE=1` and
  `--confirm-write`.
- Ariadne still does not commit, push, merge, or create PRs during backend
  execution.
- Backend doctor prints only set/unset state for secrets and writes no secret
  values.

Tests added:

- Architecture docs and ADR existence.
- Failure reason wire values.
- AgentRun lifecycle terminal invariants.
- Runtime capability snapshot persistence.
- Backend doctor secret safety.
- Project resource serialization.
- Target path validation.
- Directory lock behavior.
- BuildSkill discovery and handoff references.
- Route decision artifact.
- Progress events.
- Board Loop Trace additions.

Commands run during ARI-005 implementation:

```bash
pytest tests/test_multica_alignment.py -q
pytest -q
ruff check .
```

Interim results:

- `pytest tests/test_multica_alignment.py -q`: passed, 7 tests.
- `pytest -q`: passed, 46 tests.
- `ruff check .`: passed.

Final required command results are recorded after the acceptance run below.

Final ARI-005 acceptance run:

```bash
pytest
ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
uv run ari demo full
uv run ari ticket list
uv run ari ticket run ARI-003 --backend fake-codex
uv run ari export board
uv run ari backend doctor
```

Results:

- `pytest`: passed, 46 tests.
- `ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed.
- `uv run ari demo full`: passed.
- `uv run ari ticket list`: passed.
- `uv run ari ticket run ARI-003 --backend fake-codex`: passed.
- `uv run ari export board`: passed.
- `uv run ari backend doctor`: passed.

Latest output paths from the acceptance run:

- Board: `.ariadne/board/index.md`
- Memory: `.ariadne/memory/tickets/ticket_91c283a19122.md`
- Feishu dry-run plan: `.ariadne/feishu_plans/feishu_a152e5f8d694.json`
- Next tickets: `.ariadne/artifacts/ticket_91c283a19122/next_tickets.json`

Next recommended Build Ticket:

- ARI-006 - Add a local runtime event journal with resumable ticket-run state.

## ARI-006 Agent Teammate Mode

Implemented files:

- `ariadne_ltb/models.py`
- `ariadne_ltb/storage.py`
- `ariadne_ltb/daemon.py`
- `ariadne_ltb/journal.py`
- `ariadne_ltb/local_safety.py`
- `ariadne_ltb/orchestrator.py`
- `ariadne_ltb/board.py`
- `ariadne_ltb/cli.py`
- `tests/test_agent_teammate_mode.py`
- `README.md`
- `docs/adr/ADR-0003-agent-teammate-mode.md`
- `docs/development_report.md`

New models:

- `AgentProfile`
- `AssignmentStatus`
- `TicketAssignment`
- `CommentAuthorType`
- `CommentKind`
- `TicketComment`
- `RuntimeEvent`
- `ResumeSafety`
- `ResumePlan`

New CLI:

```bash
ari agent list
ari ticket assign <ticket_id_or_key> --to <agent_id>
ari ticket comment <ticket_id_or_key> "message"
ari ticket comments <ticket_id_or_key>
ari ticket resume <ticket_id_or_key>
ari daemon run-once
ari daemon start
ari daemon status
ari runtime journal
ari runtime recover
ari runtime locks
```

What now works:

```bash
ari ingest examples/sources/*.md
ari ticket list
ari ticket assign ARI-003 --to fake-codex
ari daemon run-once
ari ticket comments ARI-003
ari runtime journal
ari runtime recover
ari export board
```

The daemon claims exactly one queued assignment, calls `TicketRunOrchestrator`,
writes comments and runtime journal events, updates assignment status, and
exports the board.

Storage added:

- `.ariadne/agents/profiles.json`
- `.ariadne/assignments/<assignment_id>.json`
- `.ariadne/comments/<ticket_id>.jsonl`
- `.ariadne/journal/events.jsonl`
- `.ariadne/daemon/`
- `.ariadne/locks/`

Board now shows:

- Agent Assignment
- Comments
- Runtime Journal
- Daemon / Worker

Safety boundaries:

- Real Codex and Claude backends remain gated by
  `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1` plus `--confirm-execution`.
- Tests use `fake-codex` and require no network, credentials, GitHub token,
  Codex, Claude, DeepSeek, or Feishu access.
- Runtime still never auto-commits, auto-pushes, merges, or creates PRs.

Known limitations:

- `daemon start` is a simple polling loop, not an OS service.
- Recovery is conservative and writes a blocked recovery comment when unsafe.
- Resume does not implement real session resume or partial stage replay.
- Assignment queue is JSON-file based and single-user local.

Verification for ARI-006:

```bash
pytest tests/test_agent_teammate_mode.py -q
pytest -q
ruff check .
```

Interim results:

- `pytest tests/test_agent_teammate_mode.py -q`: passed, 9 tests.
- `pytest -q`: passed, 55 tests.
- `ruff check .`: passed.

Final ARI-006 acceptance run:

```bash
pytest
ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli ingest examples/sources/*.md
python3.11 -m ariadne_ltb.cli ticket list
python3.11 -m ariadne_ltb.cli ticket assign ARI-003 --to fake-codex
python3.11 -m ariadne_ltb.cli daemon run-once
python3.11 -m ariadne_ltb.cli ticket comments ARI-003
python3.11 -m ariadne_ltb.cli runtime journal
python3.11 -m ariadne_ltb.cli runtime recover
python3.11 -m ariadne_ltb.cli export board
uv run ari ingest examples/sources/*.md
uv run ari ticket list
uv run ari ticket assign ARI-003 --to fake-codex
uv run ari daemon run-once
uv run ari ticket comments ARI-003
uv run ari export board
python3.11 -m ariadne_ltb.cli agent list
python3.11 -m ariadne_ltb.cli ticket show ARI-003
python3.11 -m ariadne_ltb.cli daemon status
python3.11 -m ariadne_ltb.cli runtime locks
```

Results:

- `pytest`: passed, 55 tests.
- `ruff check .`: passed.
- Python CLI Agent Teammate Mode path: passed.
- `uv run ari` Agent Teammate Mode path: passed.
- `agent list`, `ticket show`, `daemon status`, and `runtime locks`: passed.

Latest output paths from the acceptance run:

- Board: `.ariadne/board/index.md`
- Comments: `.ariadne/comments/ticket_91c283a19122.jsonl`
- Journal: `.ariadne/journal/events.jsonl`
- Assignment: `.ariadne/assignments/assignment_d50edb01729d.json`
- Memory: `.ariadne/memory/tickets/ticket_91c283a19122.md`
- Feishu dry-run plan: `.ariadne/feishu_plans/`
- Next tickets: `.ariadne/artifacts/ticket_91c283a19122/next_tickets.json`

Next recommended Build Ticket:

- ARI-007 - Implement safe partial-stage resume using runtime journal stage
  checkpoints.
  vs stdin templates, service tier support, reasoning effort, and profile/model
  selection.

## Ariadne v1.0 Sprint

Scope:

- ARI-007 Daemon supervision and heartbeat.
- ARI-008 Retry queue and safe recovery.
- ARI-009 Multi-agent handoff loop.
- ARI-010 Real Codex teammate backend.
- ARI-011 Upstream planner and source-to-ticket intelligence.
- ARI-012 Workbench board and local UX.
- ARI-013 Evaluation, demo script, and documentation finalization.
- ARI-014 Final safety gate and release readiness.

Implemented files:

- Runtime and domain: `ariadne_ltb/models.py`, `ariadne_ltb/storage.py`,
  `ariadne_ltb/daemon.py`, `ariadne_ltb/journal.py`, `ariadne_ltb/retry.py`,
  `ariadne_ltb/handoffs.py`.
- Execution and planning: `ariadne_ltb/orchestrator.py`,
  `ariadne_ltb/execution.py`, `ariadne_ltb/ingest.py`,
  `ariadne_ltb/planner.py`, `ariadne_ltb/planner_quality.py`.
- UX and release: `ariadne_ltb/board.py`, `ariadne_ltb/board_server.py`,
  `ariadne_ltb/doctor.py`, `ariadne_ltb/cli.py`,
  `scripts/verify_v1.sh`.
- Docs: `README.md`, `docs/evaluation/v1_0_evaluation.md`,
  `docs/demo/ARIADNE_V1_DEMO_SCRIPT.md`,
  `docs/interview/PROJECT_NARRATIVE.md`,
  `docs/ops/HUMAN_DEMO_SCRIPT.md`, `docs/ops/V1_RELEASE_CHECKLIST.md`.

New CLI:

- `ari assignment list`
- `ari assignment show <assignment_id>`
- `ari assignment retry <assignment_id>`
- `ari ticket retry <ticket_id_or_key>`
- `ari ticket handoffs <ticket_id_or_key>`
- `ari daemon run-once --runtime-id <runtime_id>`
- `ari daemon start --runtime-id <runtime_id> --max-iterations <n>`
- `ari board serve`
- `ari doctor secrets`
- `ari doctor v1`

Safety boundaries:

- Real Codex and Claude execution require both
  `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1` and `--confirm-execution`.
- Real Feishu writes require both `FEISHU_ENABLE_WRITE=1` and
  `--confirm-write`.
- Ariadne runtime does not auto-commit, auto-push, auto-merge, or create PRs.
- Secret-oriented doctor commands only print set/unset.

Known limitations:

- Local single-worker runtime, not a production multi-worker scheduler.
- JSON/JSONL persistence, not Postgres.
- No production Web UI, WebSocket layer, auth, or permissions system.
- Real Codex depends on local CLI availability.
- Feishu real writes remain default-off.

Verification status:

- Final v1 command results are recorded after `scripts/verify_v1.sh` runs.
