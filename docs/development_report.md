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

- `pytest`: passed, 84 tests.
- `ruff check .`: passed.
- Python CLI v1 path passed:
  `demo full -> ingest -> ticket list -> ticket assign -> daemon run-once ->
  ticket comments -> runtime journal -> runtime recover -> daemon status ->
  export board -> backend doctor -> doctor v1`.
- `scripts/verify_v1.sh`: passed.
- Optional `uv run ari` path passed:
  `demo full`, `ticket run ARI-003 --backend fake-codex`, `ticket assign`,
  `daemon run-once`, and `export board`.

Latest output paths from the v1 acceptance run:

- Board: `.ariadne/board/index.md`
- Memory: `.ariadne/memory/tickets/ticket_91c283a19122.md`
- Feishu dry-run plan: `.ariadne/feishu_plans/`
- Next tickets: `.ariadne/artifacts/ticket_91c283a19122/next_tickets.json`

## ARI-015 Architecture Freeze

Scope:

- Added v1.0 architecture-freeze documents.
- Updated README with a concise `Ariadne v1.0 Architecture` entrypoint.
- Kept this pass docs-only: no runtime features, core business logic,
  persistence, or CLI behavior changed.

New files:

- `docs/architecture/ARIADNE_V1_ARCHITECTURE.md`
- `docs/architecture/ARIADNE_V1_OBJECT_MODEL.md`
- `docs/architecture/ARIADNE_V1_RUNTIME_FLOW.md`
- `docs/architecture/ARIADNE_V1_MULTICA_MAPPING.md`
- `docs/demo/ARIADNE_V1_DEMO_CONTRACT.md`

Updated files:

- `README.md`
- `docs/development_report.md`

Why freeze the architecture:

- Ariadne already has a working local True MVP and Agent Teammate Mode, but
  future work needs one stable explanation for product positioning, Multica
  comparison, object boundaries, demo paths, and v1.0 non-goals.
- The freeze prevents Ariadne from drifting into either a generic CLI wrapper or
  a Multica clone.

Historical product position from ARI-015:

- This section originally froze Ariadne as a Goal-driven Multi-Agent Build Team.
- That direction is now superseded by ADR-0004.
- Current product position is `Ariadne = local-first Ticket-centered Agent Workbench`.
- Learning-to-Build remains the business scenario.
- Ariadne's difference from Multica is that knowledge, feedback, memory,
  review, and codebase state update the ticket backlog before agents execute
  tickets.

Updated Multica mapping:

- `Multica = issue-centered agent work management`.
- `Ariadne = ticket-centered local agent workbench with knowledge/feedback backlog updates`.
- Ariadne adopts Multica-style agent work management: teammate identity,
  assignments, daemon/runtime, comments, provider capability, skills, resources,
  board, and future autopilot.
- Ariadne does not copy Multica's Go server, Postgres, multi-tenant workspace,
  WebSocket collaboration, daemon fleet, or frontend platform.

Current main flow:

```text
Knowledge / Feedback / Codebase / Optional Goal
  -> Ticket Backlog Update
  -> Build Tickets
  -> Agent Assignment
  -> Daemon Worker
  -> Execution Agent
  -> Reviewer Agent
  -> Memory Agent
  -> Next Tickets / Board
  -> Ticket Backlog Update
```

Current implemented bridge:

```bash
ari ingest examples/sources/*.md
ari ticket list
ari ticket assign ARI-003 --to fake-codex
ari daemon run-once
ari ticket comments ARI-003
ari runtime journal
ari export board
```

Verification status:

- `pytest`: passed, 84 tests.
- `ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli doctor v1`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `uv run ari demo full`: passed.
- `uv run ari doctor v1`: passed.
- `uv run ari export board`: passed.
- Latest board output: `.ariadne/board/index.md`.

## ARI-015 Capability Surface Freeze

Scope:

- Integrated `/Users/martinlos/Downloads/ariadne_capability_surface_pack.zip`
  into `docs/capability_surface/`.
- Added the capability-surface entrypoint
  `docs/capability_surface/ARIADNE_CAPABILITY_SURFACE.md`.
- Kept this pass docs-only: no runtime code, model, persistence, CLI, or test
  behavior was changed.

Documents written:

- `docs/capability_surface/00_START_HERE.md`
- `docs/capability_surface/01_PRODUCT_POSITIONING.md`
- `docs/capability_surface/02_MULTICA_CAPABILITY_SURFACE.md`
- `docs/capability_surface/03_ARIADNE_CAPABILITY_SURFACE.md`
- `docs/capability_surface/04_CORE_OBJECT_MODEL.md`
- `docs/capability_surface/05_PRIORITY_ROADMAP.md`
- `docs/capability_surface/06_ACCEPTANCE_FRAMEWORK.md`
- `docs/capability_surface/07_CODEX_MASTER_PROMPT.md`
- `docs/capability_surface/ARIADNE_CAPABILITY_SURFACE.md`
- `docs/capability_surface/aris/ARI-015-architecture-freeze.md`
  through `docs/capability_surface/aris/ARI-025-workbench-board-productization.md`
- `docs/capability_surface/templates/*.md`
- `docs/capability_surface/ops/CODEX_IMPLEMENTATION_RULES.md`

Capability surface decision, corrected by ADR-0004:

- Ariadne v1.x is positioned as a local-first
  `Ticket-centered Agent Workbench`.
- Multica remains the fixed benchmark for agent work-management capabilities:
  agent teammate, task lifecycle, daemon/runtime, provider capability, skills,
  squads, project resources, comments, board, and autopilot.
- Ariadne's differentiation is the ticket backlog update loop:
  `Knowledge / Feedback / Repo Context / Memory -> Build Tickets`.
- Learning-to-Build is treated as Ariadne's scenario; the ticket-centered agent
  workbench is the product capability.

Known roadmap, corrected by ADR-0004:

- P0: ARI-016 Ticket Backlog Update Loop, ARI-017 Build Team routing,
  ARI-018 real Codex teammate main demo, ARI-019 provider capability matrix.
- P1: ARI-020 skill materialization, ARI-021 project resource boundaries,
  ARI-022 memory retrieval, ARI-023 review/eval agent.
- P2: ARI-024 autopilot and recurring work, ARI-025 workbench board
  productization.

Verification status:

- `pytest`: passed, 84 tests.
- `ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli doctor v1`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- Board output: `.ariadne/board/index.md`.

## ADR-0004 Ticket-Centered Architecture Correction

Scope:

- Corrected the v1.x architecture docs from BuildGoal-first positioning to
  ticket-centered agent workbench positioning.
- Added an ADR and a new current architecture entrypoint.
- Preserved historical file paths and reports, but marked old BuildGoal-first
  instructions as superseded where future agents might otherwise execute them.
- Added a docs test to keep README and capability-surface positioning from
  drifting back to the old wording.

Files added:

- `docs/adr/ADR-0004-ticket-centered-agent-workbench.md`
- `docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md`

Files updated:

- `README.md`
- `docs/architecture/ARIADNE_V1_ARCHITECTURE.md`
- `docs/architecture/ARIADNE_V1_OBJECT_MODEL.md`
- `docs/architecture/ARIADNE_V1_RUNTIME_FLOW.md`
- `docs/architecture/ARIADNE_V1_MULTICA_MAPPING.md`
- `docs/capability_surface/00_START_HERE.md`
- `docs/capability_surface/01_PRODUCT_POSITIONING.md`
- `docs/capability_surface/02_MULTICA_CAPABILITY_SURFACE.md`
- `docs/capability_surface/03_ARIADNE_CAPABILITY_SURFACE.md`
- `docs/capability_surface/04_CORE_OBJECT_MODEL.md`
- `docs/capability_surface/05_PRIORITY_ROADMAP.md`
- `docs/capability_surface/06_ACCEPTANCE_FRAMEWORK.md`
- `docs/capability_surface/07_CODEX_MASTER_PROMPT.md`
- `docs/capability_surface/ARIADNE_CAPABILITY_SURFACE.md`
- `docs/capability_surface/aris/ARI-015-architecture-freeze.md`
- `docs/capability_surface/aris/ARI-016-build-goal-and-goal-to-ticket.md`
- `docs/capability_surface/aris/ARI-017-build-team-squad-routing.md`
- `docs/capability_surface/aris/ARI-024-autopilot-and-recurring-work.md`
- `docs/capability_surface/aris/ARI-025-workbench-board-productization.md`
- `docs/capability_surface/ops/CODEX_IMPLEMENTATION_RULES.md`
- `docs/capability_surface/templates/BUILD_GOAL_SCHEMA.md`
- `docs/capability_surface/templates/CAPABILITY_STATUS_TABLE.md`
- `docs/demo/ARIADNE_V1_DEMO_CONTRACT.md`
- `docs/development_report.md`
- `tests/test_v1_docs.py`

Architecture decision:

- Ariadne v1.x is now documented as a local-first
  `Ticket-centered Agent Workbench`.
- Goal is allowed as directional input, but it is not the runtime center,
  scheduler unit, or root state machine.
- Ticket is the work unit, audit unit, board unit, and assignment unit.
- Ariadne's differentiation is:

```text
Multica lets agents work issues.
Ariadne lets knowledge and feedback update tickets, then lets agents work tickets.
```

Corrected next roadmap:

- ARI-016: Ticket Backlog Update Loop.
- ARI-017: Knowledge / Feedback To Ticket Multi-Agent Flow.
- ARI-018: Real Codex teammate main demo.
- ARI-019: Provider Capability Matrix.

Historical notes:

- Older references to the previous BuildGoal-first direction are retained only
  where they are explicitly historical, negative, or superseded.
- `docs/capability_surface/aris/ARI-016-build-goal-and-goal-to-ticket.md`
  keeps its filename for link stability, but its current content is the
  Ticket Backlog Update Loop.

Verification status for this correction:

- `pytest`: passed, 85 tests.
- `ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli doctor v1`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed.
- `uv run ari demo full`: passed.
- `uv run ari doctor v1`: passed.
- `uv run ari export board`: passed.
- Residual scan for `Goal-driven`, `BuildGoal`, `Goal-first`,
  `Goal-to-Ticket`, and `ARI-016`: remaining matches are explicitly
  historical, superseded, negative guidance, or current ARI-016 ticket-backlog
  roadmap references.

## Ticket-Centered Review Follow-Up

Scope:

- Removed remaining actionable `ari goal ...` examples from active capability
  docs.
- Updated the v1 demo contract to use ticket-centered positioning.
- Corrected the Multica gap report so heartbeat is no longer described as
  entirely absent; only offline recovery automation remains deferred.
- Aligned README's quickstart wording with ADR-0004 terminology.
- Removed a dangerous Claude Code example flag from `.env.example`.
- Added `.secrets` to `.gitignore`.
- Strengthened docs tests to reject active-doc `ari goal` examples and current
  `goal-driven` positioning.

Verification status:

- `pytest`: passed, 86 tests.
- `ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli doctor v1`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed.
- `uv run ari demo full`: passed when run sequentially.
- `uv run ari doctor v1`: passed.
- `uv run ari export board`: passed.
- Residual scan for active `ari goal`, current `goal-driven` positioning,
  dangerous Claude flags, `handoff_path`, and `--full-auto`: no active
  guidance remains outside this report entry.

## ARI-016 Ticket Backlog Update Loop

Scope:

- Implemented the ticket-centered backlog update loop from
  `docs/capability_surface/aris/ARI-016-build-goal-and-goal-to-ticket.md`.
- Kept Goal as directional input only; no BuildGoal-first command surface was
  added.
- Used `.ariadne/backlog/updates.jsonl` as the durable local BacklogUpdate
  record because backlog updates can span multiple tickets.

Implemented files:

- `ariadne_ltb/models.py`
- `ariadne_ltb/storage.py`
- `ariadne_ltb/backlog.py`
- `ariadne_ltb/ingest.py`
- `ariadne_ltb/cli.py`
- `ariadne_ltb/board.py`
- `tests/test_backlog_update_loop.py`
- `README.md`
- `docs/capability_surface/aris/ARI-016-build-goal-and-goal-to-ticket.md`
- `docs/development_report.md`

Implemented behavior:

- `ari ingest examples/sources/*.md` now records a `source_ingest`
  BacklogUpdate.
- `ari backlog update --from-source examples/sources/*.md` explicitly updates
  the ticket backlog from source docs.
- `ari backlog history` shows update time, trigger, rationale, counts, and
  evidence refs.
- `ari ticket supersede ARI-003 --reason "..."` marks a ticket as
  `superseded`, records a backlog update, writes a ticket comment, and appends
  ticket events.
- `ari export board` now includes `Ticket Backlog Updates` and per-ticket
  `Backlog Update Trace`.

Verification status:

- `pytest`: passed, 90 tests.
- `ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli doctor v1`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed and printed
  environment/key state without secret values.
- `uv run ari demo full && uv run ari doctor v1 && uv run ari export board`:
  passed.

## Core Batch 3: Orchestration / Backend Evidence Hardening

Branch: `codex/ariadne-core-orchestration-backends-3`

This batch improves the ticket-run product path by writing a single structured
manifest for each completed orchestrator run and tightening backend blocked
result semantics.

Implemented files:

- `ariadne_ltb/models.py`
- `ariadne_ltb/orchestrator.py`
- `ariadne_ltb/execution.py`
- `tests/test_true_mvp_product_loop.py`
- `tests/test_backend_smoke_cli.py`
- `docs/development_report.md`

Implemented behavior:

- Added `ArtifactType.ORCHESTRATOR_RESULT`.
- `TicketRunOrchestrator.run_ticket(...)` now writes
  `orchestrator_result.json` under the ticket artifact directory.
- The result manifest records ticket id/key, backend, planner, build packet,
  handoff, execution result, review report, verdict, changed files, test
  command/result, memory id/path, Feishu dry-run plan id/path, next tickets,
  board path, worktree path, external execution state, and confirmation state.
- The manifest artifact is attached to the ticket and referenced in ticket
  metadata as `orchestrator_result_artifact_id` and
  `orchestrator_result_path`.
- `TicketRunResult` now exposes `orchestrator_result_path`.
- `ShellBackend` now returns a blocked `ExecutionResult` with typed
  `external_execution_blocked` failure when `--confirm-execution` is missing,
  instead of returning an untyped command failure.

Safety boundaries:

- The manifest is read-only evidence; it does not trigger external writes.
- Shell execution remains blocked unless explicitly confirmed.
- Real Codex/Claude execution remains gated by environment flag and
  confirmation.

Verification so far:

- `python3.11 -m pytest tests/test_true_mvp_product_loop.py
  tests/test_backend_smoke_cli.py -q`: passed, 20 tests.
- `python3.11 -m ruff check ariadne_ltb/orchestrator.py
  ariadne_ltb/execution.py ariadne_ltb/models.py
  tests/test_true_mvp_product_loop.py tests/test_backend_smoke_cli.py`:
  passed.
- `python3.11 -m pytest`: passed, 104 tests.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed, with external
  execution disabled and secrets redacted.
- `scripts/verify_v1.sh`: exited 0.

Known limitations:

- The manifest is an evidence artifact; it does not replace individual
  execution, review, memory, Feishu, or next-ticket artifacts.
- This batch does not change real Codex/Claude gating behavior beyond preserving
  the existing safety gates.
- `uv run ari ticket list && uv run ari ticket run ARI-003 --backend
  fake-codex`: passed.

Follow-up: board provider audit visibility:

- `ariadne_ltb/board.py` now renders a per-ticket `Provider Audit Artifacts`
  section for executed tickets.
- The board links the orchestrator result manifest, execution log, git diff,
  changed files artifact, test output artifact, memory record, Feishu dry-run
  plan, next tickets artifact, and board path.
- The board also shows manifest-derived backend, execution result, review
  report, review verdict, external execution enabled state, and confirmation
  state.
- This completes the visible board evidence part of `ARI-MUL-36: Provider
  execution audit artifacts`.

Follow-up verification:

- `python3.11 -m pytest tests/test_true_mvp_product_loop.py
  tests/test_v1_board_ux.py -q`: passed, 17 tests.
- `python3.11 -m ruff check ariadne_ltb/board.py
  tests/test_true_mvp_product_loop.py`: passed.
- `python3.11 -m pytest`: passed, 105 tests.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed, with external
  execution disabled and secrets redacted.
- `scripts/verify_v1.sh`: exited 0.
- Manual backlog smoke with `python3.11 -m ariadne_ltb.cli --root
  /tmp/ariadne-backlog-smoke backlog update --from-source
  examples/sources/*.md`, `backlog history`, `ticket supersede`, and
  `export board`: passed. The board showed both global `Ticket Backlog
  Updates` and per-ticket `Backlog Update Trace` sections.

Post-merge review hardening:

- Source ingest now deduplicates repeated paths in a single backlog update.
- Local source identity is path-stable; editing the same source path updates
  the existing ticket instead of creating a duplicate ticket.
- Re-ingesting a source no longer reopens a `superseded` ticket.
- Superseding a ticket cancels open assignments for that ticket.
- Daemon and orchestrator paths refuse to execute `superseded` tickets.
- Backlog history and board export tolerate malformed backlog JSONL lines by
  ignoring invalid records.
- CLI error paths for missing source files and unknown tickets now return
  concise exit-2 messages instead of tracebacks.

Verification after review hardening:

- `pytest tests/test_backlog_update_loop.py -q`: passed, 11 tests.
- `pytest tests/test_agent_teammate_mode.py tests/test_true_mvp_product_loop.py
  tests/test_1_0_full_demo.py tests/test_v1_daemon_supervision.py
  tests/test_backlog_update_loop.py -q`: passed, 43 tests.
- `pytest`: passed, 97 tests.
- `ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli doctor v1`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed and printed
  environment/key state without secret values.
- `uv run ari demo full && uv run ari doctor v1 && uv run ari export board`:
  passed.

## Core Batch 4: Execution Sandbox Permission Profiles

Branch: `codex/ariadne-core-orchestration-backends-3`

This batch completes `ARI-MUL-39 / LOC-44` by making Ariadne's local execution
boundaries explicit and visible before backend execution.

Implemented files:

- `ariadne_ltb/permissions.py`
- `ariadne_ltb/models.py`
- `ariadne_ltb/orchestrator.py`
- `ariadne_ltb/execution.py`
- `ariadne_ltb/board.py`
- `tests/test_true_mvp_product_loop.py`
- `tests/test_backend_smoke_cli.py`
- `tests/test_v1_board_ux.py`
- `docs/development_report.md`

Implemented behavior:

- Added `ExecutionPermissionProfile` and `ArtifactType.PERMISSION_PROFILE`.
- `TicketRunOrchestrator` now writes
  `execution_permission_profile.json` for each ticket run.
- The permission profile records target repo, allowed paths, environment
  allowlist, network policy, git-operation policy, dangerous git operations,
  external execution state, confirmation state, command, and test command.
- The provider-facing handoff now includes an `Execution Permission Profile`
  section.
- `RouteDecision` and `orchestrator_result.json` reference the permission
  profile.
- `ari export board` now shows `Execution Permission Profile` and links it
  from `Provider Audit Artifacts`.
- `FakeCodexBackend`, `ShellBackend`, `CodexBackend`, and `ClaudeCodeBackend`
  share local permission validation for target repo, allowed paths, dangerous
  git commands, and changed files outside the allowed paths.

Safety boundaries:

- This is a local policy layer, not an OS-level sandbox.
- Dangerous direct shell git operations such as `git push`, `git merge`, and
  `git reset` are blocked by default.
- Real Codex/Claude execution remains gated by
  `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1` and `--confirm-execution`.
- The profile is recorded as evidence and injected into handoff context, but it
  does not grant new privileges.

Verification:

- `python3.11 -m pytest tests/test_true_mvp_product_loop.py
  tests/test_backend_smoke_cli.py tests/test_v1_board_ux.py -q`: passed, 26
  tests.
- `python3.11 -m ruff check ariadne_ltb/permissions.py
  ariadne_ltb/execution.py ariadne_ltb/orchestrator.py ariadne_ltb/board.py
  ariadne_ltb/models.py tests/test_true_mvp_product_loop.py
  tests/test_backend_smoke_cli.py tests/test_v1_board_ux.py`: passed.
- `python3.11 -m pytest`: passed, 107 tests.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed, with external
  execution disabled and secrets redacted.
- `scripts/verify_v1.sh`: exited 0.

Known limitations:

- Permission profiles are enforced at Ariadne's Python backend boundary and by
  changed-file review after execution. They do not provide kernel-level
  isolation.
- Provider adapters cannot physically prevent an external Codex/Claude process
  from attempting side effects beyond the handoff policy; Ariadne still blocks
  external execution by default and records/reviews changed files.

## Core Batch 5: Prompt Injection Guard for Sources and Skills

Branch: `codex/ariadne-core-orchestration-backends-3`

This batch completes `ARI-MUL-38 / LOC-43` by treating external sources and
local BuildSkill bodies as untrusted context unless explicitly trusted.

Implemented files:

- `ariadne_ltb/prompt_guard.py`
- `ariadne_ltb/ingest.py`
- `ariadne_ltb/planner.py`
- `ariadne_ltb/review.py`
- `ariadne_ltb/skills.py`
- `ariadne_ltb/board.py`
- `ariadne_ltb/storage.py`
- `tests/test_prompt_guard.py`
- `tests/test_v1_daemon_supervision.py`
- `docs/development_report.md`

Implemented behavior:

- Added prompt-injection pattern detection for source documents and BuildSkill
  bodies.
- Source document metadata now records `trust_boundary`,
  `prompt_injection_findings`, and `prompt_injection_warning_count`.
- Build Packet evidence snippets are quoted as untrusted source context.
- Deterministic and LLM planner outputs carry prompt-guard metadata.
- LLM planner prompt explicitly says source content is untrusted data and must
  not be followed as instruction.
- Handoff prompts now include a `Trust Boundary` section.
- BuildSkill references are marked as untrusted metadata. If a skill body
  contains prompt-injection patterns, Ariadne withholds body-derived
  descriptions and reports a warning count.
- Reviewer reports prompt-injection warnings without treating the source text as
  executable instruction.
- Board shows `Prompt Injection Guard` and trust-boundary status per ticket.
- `list_worker_heartbeats()` now ignores partial or invalid heartbeat files,
  fixing a board-export race observed during CLI verification.

Safety boundaries:

- The guard is a deterministic local scanner, not a complete content-security
  model.
- Warnings do not execute or mutate code. They are audit evidence for planner,
  reviewer, and board.
- External execution remains blocked by default and still requires explicit
  confirmation.

Verification:

- `python3.11 -m pytest tests/test_prompt_guard.py
  tests/test_v1_daemon_supervision.py tests/test_true_mvp_product_loop.py
  tests/test_v1_board_ux.py -q`: passed, 24 tests.
- Targeted `ruff check`: passed.
- `python3.11 -m pytest`: passed, 110 tests.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed, with external
  execution disabled and secrets redacted.
- `scripts/verify_v1.sh`: exited 0.

Known limitations:

- Pattern matching is intentionally conservative and deterministic. It will not
  catch every possible adversarial prompt.
- The guard prevents source/skill text from being treated as higher-priority
  instructions in Ariadne handoff and review artifacts; it is not a provider
  model jailbreak detector.

## Core Batch 6: Secret and Sensitive File Safety Doctor

Branch: `codex/ariadne-core-orchestration-backends-3`

This batch completes `ARI-MUL-37 / LOC-42` by adding local secret-safety checks
for doctor commands, backend execution preflight, and board visibility.

Implemented files:

- `ariadne_ltb/secret_safety.py`
- `ariadne_ltb/execution.py`
- `ariadne_ltb/doctor.py`
- `ariadne_ltb/cli.py`
- `ariadne_ltb/board.py`
- `tests/test_secret_safety.py`
- `tests/test_backend_smoke_cli.py`
- `tests/test_v1_doctor_release.py`
- `docs/development_report.md`

Implemented behavior:

- Added deterministic scanning for sensitive filenames, sensitive directories,
  private key markers, and common token/key assignment patterns.
- Scan results report paths, line numbers, and `[REDACTED]`, never secret
  values.
- `ari doctor secrets` now reports environment set/unset state plus local secret
  scan status.
- `ari backend doctor` reports secret scan status without printing values.
- `ari doctor v1` includes secret scan status in the readiness output.
- Board system summary shows `Secret safety` and `Secret findings`.
- Backend execution preflight blocks commands that reference sensitive paths,
  allowed paths that include sensitive paths, or target repositories containing
  detected sensitive material.
- Tests construct fake tokens at runtime so no token-like literals remain in the
  repository.

Safety boundaries:

- This is a local deterministic scanner, not a full secret-detection service.
- `.git`, `.ariadne`, virtualenvs, `node_modules`, and cache directories are
  skipped to avoid scanning generated local state.
- Block messages cite paths only and redact values.

Verification:

- `python3.11 -m pytest tests/test_secret_safety.py
  tests/test_v1_doctor_release.py tests/test_backend_smoke_cli.py
  tests/test_true_mvp_product_loop.py -q`: passed, 31 tests.
- Targeted `ruff check`: passed.
- Repository secret scan: ok, 0 findings.
- `python3.11 -m pytest`: passed, 114 tests.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed and reported
  `secret scan: ok` with 0 findings.
- `python3.11 -m ariadne_ltb.cli doctor secrets`: passed and reported
  `secret scan: ok` with 0 findings.
- `scripts/verify_v1.sh`: exited 0.

Known limitations:

- Pattern matching is intentionally conservative and may miss uncommon secret
  formats.
- The scanner is designed for local preflight and review evidence; it is not a
  replacement for dedicated repository secret scanning in CI.

## Core Batch 7: Store Invariant Doctor

Branch: `codex/ariadne-core-orchestration-backends-3`

This batch completes `ARI-MUL-25 / LOC-30` by adding a local read-only doctor
for impossible Ariadne workspace states before agents trust `.ariadne/`.

Implemented files:

- `ariadne_ltb/models.py`
- `ariadne_ltb/storage.py`
- `ariadne_ltb/store_doctor.py`
- `ariadne_ltb/doctor.py`
- `ariadne_ltb/cli.py`
- `ariadne_ltb/board.py`
- `scripts/verify_v1.sh`
- `tests/test_store_doctor.py`
- `docs/development_report.md`

Implemented behavior:

- Added typed store invariant severities and reasons.
- Added `StoreInvariantIssue` and `StoreInvariantReport` models.
- Added `ari doctor store` / `python3.11 -m ariadne_ltb.cli doctor store`.
- The store doctor writes `.ariadne/doctor/store_invariants.json`.
- The doctor validates malformed JSON, malformed JSONL, duplicate ticket keys,
  missing BuildPackets, missing AgentRuns, missing artifact indexes, missing
  artifact payload files, orphan artifacts, broken assignment links, broken
  handoff links, broken memory/review/execution links, invalid AgentRun
  lifecycle states, invalid assignment lifecycle states, and stale directory
  locks.
- Stale locks are warnings; structural corruption and broken references are
  errors.
- Run link problems use the typed `broken_run_link` reason instead of being
  collapsed into assignment failures.
- `ari doctor v1` now includes store invariant status, error count, and warning
  count.
- Board system summary and `## Store Invariants` show the latest store doctor
  report and first issues.
- `scripts/verify_v1.sh` now runs `doctor store`.

Safety boundaries:

- The doctor is read-only. It reports repair evidence but does not delete,
  rewrite, or auto-heal state.
- Invalid JSON and invalid model files are reported deterministically instead
  of crashing the doctor.
- Machine-readable output is available through `--json` for future frontend or
  automation consumption.

Verification:

- `python3.11 -m pytest tests/test_store_doctor.py -q`: passed, 6 tests.
- `python3.11 -m pytest tests/test_v1_doctor_release.py
  tests/test_v1_board_ux.py tests/test_true_mvp_product_loop.py
  tests/test_store_doctor.py -q`: passed, 27 tests.

Known limitations:

- The doctor reports broken state but intentionally does not generate an
  automatic repair plan yet.
- Artifact orphan detection is local-store based; it does not try to infer
  intent from unindexed loose files under `.ariadne/artifacts/`.

## Core Batch 8: Atomic Local Claim and Lease

Branch: `codex/ariadne-core-orchestration-backends-3`

This batch implements `ARI-MUL-01 / LOC-6` by making local daemon assignment
claiming atomic and lease-backed.

Implemented files:

- `ariadne_ltb/models.py`
- `ariadne_ltb/storage.py`
- `ariadne_ltb/daemon.py`
- `ariadne_ltb/store_doctor.py`
- `ariadne_ltb/board.py`
- `tests/test_assignment_claim_lease.py`
- `docs/development_report.md`

Implemented behavior:

- `TicketAssignment` now carries `lease_expires_at`.
- Terminal assignment transitions clear the lease.
- `AriadneStore.claim_next_assignment()` performs queue selection and claim
  update under a local file lock at `.ariadne/assignments/.claim.lock`.
- Two local daemon workers cannot claim the same queued assignment.
- Expired claimed/running assignments can be reclaimed deterministically by a
  new runtime.
- Reclaimed assignments record `lease_reclaimed_at`,
  `lease_reclaimed_from_runtime_id`, and `lease_reclaimed_from_status`.
- Daemon claim journal events include `claimed_by_runtime_id`,
  `lease_expires_at`, and reclaim metadata.
- Board assignment sections show claim runtime and lease expiry.
- Store doctor reports stale assignment leases as warnings with the typed
  `stale_assignment_lease` reason.

Safety boundaries:

- Lease reclaim only happens after expiry.
- This is a local filesystem lock, not a distributed lock.
- The runtime still does not auto-commit, auto-push, auto-merge, or create PRs.

Verification:

- `python3.11 -m pytest tests/test_assignment_claim_lease.py
  tests/test_v1_daemon_supervision.py tests/test_agent_teammate_mode.py
  tests/test_store_doctor.py -q`: passed, 24 tests.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m pytest`: passed, 124 tests.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed.
- `python3.11 -m ariadne_ltb.cli doctor store`: passed with
  `store invariants: ok`, `errors: 0`, and `warnings: 0`.
- `scripts/verify_v1.sh`: exited 0.

Known limitations:

- Lease duration is currently fixed by the caller default; there is no CLI flag
  yet to configure it per daemon run.
- There is no heartbeat-based lease extension yet. Long-running assignments
  should either complete within the lease or add a future renewal step.
