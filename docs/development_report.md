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

- Local memory retrieval now exists as deterministic keyword search over
  `.ariadne/memory/tickets/*.json`; it is not a vector index.
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

## Core Batch 9: Unified Failure Pipeline

Branch: `codex/ariadne-core-orchestration-backends-3`

This batch implements `ARI-MUL-02 / LOC-7` by centralizing assignment failure,
block, and cancellation side effects.

Implemented files:

- `ariadne_ltb/failure.py`
- `ariadne_ltb/daemon.py`
- `ariadne_ltb/backlog.py`
- `tests/test_failure_pipeline.py`
- `docs/development_report.md`

Implemented behavior:

- Added `record_assignment_failure()` as the common local failure pipeline.
- The pipeline updates assignment status, failure reason, blocker, lease state,
  ticket status, ticket event log, blocker comment, and runtime journal event.
- Runtime journal events carry typed `FailureReason` and
  `retry_recommendation` metadata.
- Safe retry reasons produce `ari ticket retry <ticket-key>`.
- Unsafe or unknown reasons produce `human_review_required`.
- Daemon exception, execution blocked, and reviewer blocked paths now use the
  same failure pipeline.
- Backlog supersede now cancels open assignments through the same failure
  pipeline while preserving the ticket's `superseded` status.

Safety boundaries:

- The handler records state and recommendations only; it does not auto-retry,
  auto-commit, auto-push, auto-merge, or create PRs.
- Retry safety remains conservative and still requires explicit retry commands.

Verification:

- `python3.11 -m pytest tests/test_failure_pipeline.py
  tests/test_agent_teammate_mode.py tests/test_backlog_update_loop.py -q`:
  passed, 24 tests.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m pytest`: passed, 128 tests.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed.
- `python3.11 -m ariadne_ltb.cli doctor store`: passed with
  `store invariants: ok`, `errors: 0`, and `warnings: 0`.
- `scripts/verify_v1.sh`: exited 0.

Known limitations:

- Orchestrator-level blocked `ExecutionResult` creation is still separate from
  assignment failure recording. It returns execution evidence, while the daemon
  records assignment failure state.
- Retry policy is still a small typed allowlist, not a learned policy.

## Core Batch 10: Run Message Stream

Branch: `codex/ariadne-core-orchestration-backends-3`

This batch implements `ARI-MUL-03 / LOC-8` by adding a per-AgentRun message
stream that can be consumed incrementally by CLI users, automation, and the
future frontend without scraping long ticket comments.

Implemented files:

- `ariadne_ltb/models.py`
- `ariadne_ltb/storage.py`
- `ariadne_ltb/planner.py`
- `ariadne_ltb/orchestrator.py`
- `ariadne_ltb/runtime.py`
- `ariadne_ltb/cli.py`
- `ariadne_ltb/board.py`
- `tests/test_run_messages.py`
- `docs/development_report.md`

Implemented behavior:

- Added `RunMessageType` and `RunMessage`.
- Added `.ariadne/runs/<run_id>/messages.jsonl` per-run streams while keeping
  the existing `.ariadne/runs/<run_id>.json` AgentRun snapshots.
- Added per-run `.messages.lock` locking for appends.
- Added `AriadneStore.reset_run_messages()`, `append_run_message()`, and
  `list_run_messages(run_id, since=...)`.
- `since` is an exclusive cursor: `--since 3` returns messages with `seq > 3`.
- Planner, orchestrator execution/review/memory runs, and the original kernel
  `PipelineEngine` now write start, artifact/result/error, and finish messages.
- Reused deterministic run IDs reset their stream at run start so repeated demo
  runs do not mix old and new message logs.
- Added `ari run messages <run_id> --since N` and the fallback
  `python3.11 -m ariadne_ltb.cli run messages <run_id> --since N`.
- CLI message output is deterministic JSONL with sorted keys and compact
  separators.
- Board Agent Run Timeline now links each run's `messages.jsonl` without
  inlining message bodies.

Safety boundaries:

- Message streams are local review artifacts only; they do not execute actions.
- Board links message files but does not inline stdout/stderr/message bodies.
- Message append locking is local filesystem locking, not a distributed stream
  service.
- The real Codex and Claude execution paths remain safety-gated and unchanged.

Verification:

- `python3.11 -m pytest tests/test_run_messages.py -q`: passed, 6 tests.
- `python3.11 -m ruff check ariadne_ltb tests/test_run_messages.py`: passed.
- `python3.11 -m pytest`: passed, 134 tests.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed.
- `python3.11 -m ariadne_ltb.cli doctor store`: passed with
  `store invariants: ok`, `errors: 0`, and `warnings: 0`.
- `scripts/verify_v1.sh`: exited 0.

Known limitations:

- Store doctor checks JSONL syntax generically, but it does not yet validate
  run-message schema, missing run links, duplicate `seq`, or orphan run message
  directories as first-class invariant reasons.
- The message stream is pull-based through local files and CLI. It is not a
  WebSocket or hosted event stream.

## Core Batch 11: Thread-Aware Comments

Branch: `codex/ariadne-core-orchestration-backends-3`

This batch implements `ARI-MUL-04 / LOC-9` by turning flat ticket comments into
thread-aware local conversations while keeping old `.ariadne/comments/*.jsonl`
records readable.

Implemented files:

- `ariadne_ltb/models.py`
- `ariadne_ltb/storage.py`
- `ariadne_ltb/cli.py`
- `ariadne_ltb/board.py`
- `ariadne_ltb/daemon.py`
- `ariadne_ltb/orchestrator.py`
- `ariadne_ltb/failure.py`
- `ariadne_ltb/handoffs.py`
- `ariadne_ltb/retry.py`
- `tests/test_thread_comments.py`
- `docs/development_report.md`

Implemented behavior:

- `TicketComment` now has `parent_comment_id` and `thread_id`.
- Legacy comment JSONL without those fields still loads; legacy comments become
  their own thread roots.
- `AriadneStore.add_comment()` supports `parent_comment_id` replies and
  explicit `thread_id` for system lifecycle threads.
- Added comment query helpers for roots, one thread, recent active threads,
  `since`, and `tail`.
- `ari ticket comment <ticket> <message> --reply-to <comment-id>` creates a
  threaded human reply.
- `ari ticket comments` now supports `--roots`, `--thread`, `--recent` /
  `--recent-threads`, `--tail`, and `--since`.
- Assignment root comments use the assignment id as thread id.
- Daemon claim/done comments, orchestrator progress/review/memory comments,
  handoff comments, retry comments, and failure/blocker comments now attach to
  the assignment thread when an assignment exists.
- Board top-level Agent Comments shows recent active thread summaries.
- Per-ticket board sections show comment ids, thread ids, parent ids, and a
  `### Comment Threads` summary table.

Safety boundaries:

- This is a local JSONL schema evolution only; no server, auth, WebSocket, or
  hosted comment service was introduced.
- Existing comments are not rewritten or migrated.
- Thread-aware comments do not perform retries or execution by themselves.

Verification:

- `python3.11 -m pytest tests/test_thread_comments.py -q`: passed, 5 tests.
- `python3.11 -m ruff check ariadne_ltb tests/test_thread_comments.py`: passed.
- `python3.11 -m pytest`: passed, 139 tests.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed.
- `python3.11 -m ariadne_ltb.cli doctor store`: passed with
  `store invariants: ok`, `errors: 0`, and `warnings: 0`.
- `scripts/verify_v1.sh`: exited 0.

Known limitations:

- There is no dedicated `ari ticket comments --json` output yet.
- Recent-thread summaries are local CLI/board views, not a hosted inbox.
- Store doctor validates comment JSONL syntax and model shape generically, but
  does not yet report broken parent/thread links as a first-class invariant.

## Core Batch 12: Skill Materialization

Branch: `codex/ariadne-core-orchestration-backends-3`

This batch implements `ARI-MUL-05 / LOC-10` by upgrading BuildSkill packs from
handoff-only references into local provider-visible materialized context.

Implemented files:

- `ariadne_ltb/models.py`
- `ariadne_ltb/storage.py`
- `ariadne_ltb/skills.py`
- `ariadne_ltb/orchestrator.py`
- `ariadne_ltb/execution.py`
- `ariadne_ltb/board.py`
- `tests/test_skill_materialization.py`
- `docs/development_report.md`

Implemented behavior:

- Added `ArtifactType.SKILL_BUNDLE`.
- Added `BuildSkillMaterialization`.
- Added `.ariadne/skills/<ticket-key>/` as the local provider-visible skill
  bundle directory.
- Added `select_build_skills()` and `materialize_build_skills()`.
- Materialization copies selected `.skills/*/SKILL.md` files into
  `.ariadne/skills/<ticket-key>/<skill-name>/SKILL.md`.
- Missing default skills produce warning entries instead of crashes.
- BuildSkill bodies with prompt-injection findings are withheld and recorded as
  warnings instead of being copied to provider-visible context.
- Orchestrator writes `skill_bundle.json` as a ticket artifact before
  execution.
- Coding handoffs now include `## Materialized BuildSkill Bundle` with the
  skill bundle artifact path and provider-visible skill directory.
- `ExecutionContext` now carries `skill_bundle_path` and `provider_skill_dir`.
- FakeCodexBackend reports whether the skill bundle and provider skill
  directory are available.
- CodexBackend / ClaudeCodeBackend scaffold paths receive the materialized
  skill locations through the handoff file.
- Board `### Build Skills` now shows the skill bundle path, provider-visible
  directory, included skills, and withheld skill warnings.

Safety boundaries:

- Ariadne does not write to global Codex, Claude, or user skill directories.
- Skill materialization is local to `.ariadne/skills/<ticket-key>/`.
- BuildSkill bodies remain lower-priority context; handoff text explicitly
  says they are not higher-priority instructions.
- Prompt-injection findings in skill bodies cause the skill body to be withheld.
- Real Codex / Claude execution remains gated by existing external execution
  controls.

Verification:

- `python3.11 -m pytest tests/test_skill_materialization.py -q`: passed, 4
  tests.
- `python3.11 -m ruff check ariadne_ltb tests/test_skill_materialization.py`:
  passed.
- `python3.11 -m pytest`: passed, 143 tests.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed.
- `python3.11 -m ariadne_ltb.cli doctor store`: passed with
  `store invariants: ok`, `errors: 0`, and `warnings: 0`.
- `scripts/verify_v1.sh`: exited 0.

Known limitations:

- Skill selection is still a conservative default set, not a learned router.
- Provider-specific packaging is a local file bundle referenced from the
  handoff, not native Codex/Claude skill installation.
- Store doctor does not yet validate orphaned `.ariadne/skills/<ticket-key>/`
  directories.

## Core Batch 13: Feedback-to-Ticket Update Engine

Branch: `codex/ariadne-core-orchestration-backends-3`

This batch implements `ARI-MUL-06 / LOC-11` by making ticket runs write
feedback-driven `BacklogUpdate` records and materialize selected follow-up
tickets from review, memory, and codebase observations.

Implemented files:

- `ariadne_ltb/models.py`
- `ariadne_ltb/backlog.py`
- `ariadne_ltb/orchestrator.py`
- `ariadne_ltb/cli.py`
- `ariadne_ltb/board.py`
- `tests/test_backlog_update_loop.py`
- `docs/development_report.md`

Implemented behavior:

- Added `TicketChangeType.NO_OP` for feedback that is observed but should not
  mutate the ticket set.
- Added `record_feedback_backlog_updates()` to generate backlog updates from:
  - execution result;
  - review feedback;
  - memory gaps;
  - codebase changed-file observations.
- `TicketRunOrchestrator.run_ticket()` now calls the feedback backlog engine
  after next-ticket generation and before board export.
- High and medium priority next-ticket suggestions are materialized as
  idempotent follow-up Build Tickets with Build Packets.
- Low priority suggestions remain artifact-only and are recorded as no-op
  backlog decisions.
- Source tickets receive update trace events when follow-up tickets are created
  from their run feedback.
- Added public helpers for explicit downgrade and no-op backlog decisions.
- `ari backlog history` now prints change counts and per-ticket change lines.
- `ari ticket run` prints generated backlog update ids.
- Board top-level backlog section and per-ticket `Backlog Update Trace` now
  show change-type counts, evidence refs, and no-op/downgrade records.

Safety boundaries:

- Generated follow-up tickets are local JSON artifacts only.
- No auto-commit, auto-push, auto-merge, PR creation, real Feishu write, or
  external execution behavior was added.
- Real Codex and Claude execution remain gated by existing controls.
- Generated follow-up Build Packets are conservative deterministic scaffolds and
  can be replanned before execution.

Verification:

- `python3.11 -m pytest tests/test_backlog_update_loop.py -q`: passed, 14
  tests.
- `python3.11 -m ruff check ariadne_ltb/backlog.py ariadne_ltb/orchestrator.py ariadne_ltb/cli.py ariadne_ltb/board.py ariadne_ltb/models.py tests/test_backlog_update_loop.py`:
  passed.
- `python3.11 -m pytest tests/test_true_mvp_product_loop.py tests/test_v1_board_ux.py tests/test_v1_daemon_supervision.py -q`:
  passed, 22 tests.
- `python3.11 -m pytest`: passed, 146 tests.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli ticket list`: passed and showed generated
  review follow-up tickets.
- `python3.11 -m ariadne_ltb.cli ticket run ARI-003 --backend fake-codex`:
  passed and printed four backlog update ids.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; external execution
  remained disabled and no secrets were printed.
- `python3.11 -m ariadne_ltb.cli doctor store`: passed with
  `store invariants: ok`, `errors: 0`, and `warnings: 0`.
- `scripts/verify_v1.sh`: exited 0.
- Optional `uv run ari ticket list`: passed.
- Optional `uv run ari demo full`: passed.
- Optional `uv run ari export board`: passed.
- Optional `uv run ari backend doctor`: passed.
- Optional `uv run ari ticket run ARI-003 --backend fake-codex`: passed and
  printed four backlog update ids.

Known limitations:

- Follow-up ticket materialization is deterministic and conservative; it is not
  yet ranked by a learned planner.
- Backlog updates are append-only JSONL records. There is no compaction or
  review UI beyond CLI and static board export.
- Generated follow-up tickets use review-source documents derived from
  `next_tickets.json`; richer source provenance can be added later.

## Core Batch 14: Build Team / Squad Routing

Branch: `codex/ariadne-core-orchestration-backends-3`

This batch implements `ARI-MUL-07 / LOC-12` by adding a local Multica-style
Build Team routing layer without introducing a hosted squad service.

Implemented files:

- `ariadne_ltb/models.py`
- `ariadne_ltb/storage.py`
- `ariadne_ltb/team.py`
- `ariadne_ltb/cli.py`
- `ariadne_ltb/board.py`
- `tests/test_agent_teammate_mode.py`
- `docs/development_report.md`

Implemented behavior:

- Added `BuildTeam` as a local-first team configuration model.
- Added default `build-team` / `Ariadne Build Team` with Build Lead,
  implementer, reviewer, and memory role mappings.
- Added `.ariadne/agents/teams.json` persistence with default-team bootstrapping.
- Added `ari team list` and `ari team show <team>`.
- `ari ticket assign <ticket> --to build-team` now routes through Build Lead,
  writes `route_decision.json`, comments on the assignment thread, writes a
  runtime route event, and creates the selected implementer assignment.
- Route decisions now include `build_team_id`, `build_team_name`,
  `team_role_agent_ids`, `selected_agent_id`, and `selected_agent_name`.
- The static board shows configured Build Teams and per-ticket route team /
  selected agent details.
- Existing direct agent assignment remains unchanged.

Safety boundaries:

- Build Team routing is local JSON state, not a Multica server clone.
- No Postgres, WebSocket, multi-workspace auth, hosted queue, default external
  execution, real Feishu write, commit, push, merge, or PR creation was added.
- Team routing delegates to the existing assignment and daemon runtime path.

Verification:

- `python3.11 -m pytest tests/test_agent_teammate_mode.py -q`: passed, 12
  tests.
- `python3.11 -m pytest tests/test_multica_alignment.py tests/test_v1_daemon_supervision.py tests/test_true_mvp_product_loop.py -q`:
  passed, 26 tests.
- `python3.11 -m pytest tests/test_agent_teammate_mode.py tests/test_multica_alignment.py -q`:
  passed, 19 tests.
- `python3.11 -m ruff check ariadne_ltb/models.py ariadne_ltb/storage.py ariadne_ltb/team.py ariadne_ltb/cli.py ariadne_ltb/board.py tests/test_agent_teammate_mode.py`:
  passed.
- `python3.11 -m pytest`: passed, 149 tests.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli team list`: passed.
- `python3.11 -m ariadne_ltb.cli team show build-team`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli ticket list`: passed.
- `python3.11 -m ariadne_ltb.cli ticket assign ARI-003 --to build-team`:
  passed and wrote a route decision artifact.
- `python3.11 -m ariadne_ltb.cli ticket run ARI-003 --backend fake-codex`:
  passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; no secrets were
  printed and external execution remained disabled.
- `python3.11 -m ariadne_ltb.cli doctor store`: passed with
  `store invariants: ok`, `errors: 0`, and `warnings: 0`.
- `scripts/verify_v1.sh`: exited 0.
- Optional `uv run ari team list`: passed.
- Optional `uv run ari team show build-team`: passed.
- Optional `uv run ari demo full`: passed.
- Optional `uv run ari export board`: passed.
- Optional `uv run ari backend doctor`: passed.

Known limitations:

- Build Team selection is deterministic configuration, not learned routing.
- Only the implementer assignment is queued explicitly; reviewer and memory
  roles still run inside the existing `TicketRunOrchestrator` loop.
- Team configuration has no CLI mutation command yet; defaults are bootstrapped
  and custom teams can be edited through the local JSON file.

## Core Batch 15: Provider Capability Matrix

Branch: `codex/ariadne-core-orchestration-backends-3`

This batch implements `ARI-MUL-08 / LOC-13` by turning backend diagnostics from
a coarse availability check into a persisted provider capability matrix.

Implemented files:

- `ariadne_ltb/models.py`
- `ariadne_ltb/runtime.py`
- `ariadne_ltb/cli.py`
- `ariadne_ltb/board.py`
- `tests/test_provider_capability_matrix.py`
- `README.md`
- `docs/development_report.md`

Implemented behavior:

- Extended `RuntimeCapability` with explicit provider capabilities for
  prompt-file input, stdin prompt input, session resume, MCP, skill
  materialization, model selection, reasoning effort, timeout behavior, diff
  capture, test capture, git status capture, safety-gate env vars, template env
  vars, disabled reasons, and notes.
- Updated `collect_runtime_capabilities()` to produce an honest local matrix for
  `fake-codex`, `dry-run`, `shell`, `codex`, and `claude-code`.
- Added `ari backend matrix` with optional `--json`; it persists
  `.ariadne/runtimes/capability_snapshot.json` and prints only env names plus
  set/unset status, not secret values or template contents.
- Kept `ari backend doctor` as the health/safety diagnostic while sharing the
  same enhanced snapshot persistence.
- Updated the static board `Backend Capability` section with a
  `Provider Capability Matrix` showing command availability, prompt mode,
  skills, timeout, diff/test capture, external gate, template env state, and
  blocked reasons.
- Updated per-ticket runtime capability rendering so orchestrator artifacts show
  the same matrix details.
- Documented `ari backend matrix` in the README.

Safety boundaries:

- Real `codex`, `claude-code`, and `shell` execution remain gated by
  `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1` and `--confirm-execution`.
- `backend matrix` does not execute providers.
- Command templates are not printed, only whether their env vars are set.
- No Feishu writes, commits, pushes, merges, PR creation, server runtime,
  Postgres, WebSocket, multi-workspace auth, or hosted UI was added.

Verification:

- `python3.11 -m pytest tests/test_provider_capability_matrix.py tests/test_backend_smoke_cli.py::test_backend_doctor_reports_gates_without_secrets tests/test_multica_alignment.py::test_runtime_capability_snapshot_and_backend_doctor_secret_safety -q`:
  passed, 5 tests.
- `python3.11 -m ruff check ariadne_ltb/models.py ariadne_ltb/runtime.py ariadne_ltb/cli.py ariadne_ltb/board.py tests/test_provider_capability_matrix.py`:
  passed.
- `python3.11 -m pytest tests/test_provider_capability_matrix.py tests/test_backend_smoke_cli.py tests/test_multica_alignment.py -q`:
  passed, 19 tests.
- `python3.11 -m pytest`: passed, 152 tests.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli backend matrix`: passed and wrote
  `.ariadne/runtimes/capability_snapshot.json`.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli ticket list`: passed.
- `python3.11 -m ariadne_ltb.cli ticket run ARI-003 --backend fake-codex`:
  passed with reviewer verdict `pass`.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; no secrets were
  printed and external execution remained disabled.
- `python3.11 -m ariadne_ltb.cli doctor store`: passed with
  `store invariants: ok`, `errors: 0`, and `warnings: 0`.
- `scripts/verify_v1.sh`: exited 0.
- Optional `uv run ari backend matrix`: passed.
- Optional `uv run ari demo full`: passed.
- Optional `uv run ari ticket list`: passed.
- Optional `uv run ari ticket run ARI-003 --backend fake-codex`: passed.
- Optional `uv run ari export board`: passed.
- Optional `uv run ari backend doctor`: passed.

Known limitations:

- Session resume, MCP, model selection, and reasoning-effort controls are
  represented as explicit unsupported capabilities until real adapters wire
  those controls.
- Capability rows are deterministic local declarations, not provider-discovered
  live introspection beyond command availability and env-gate state.
- `dry-run` intentionally reports no diff/test capture because it does not run a
  target command or test suite.

## Core Batch 16: Real Codex Teammate Main Demo

Branch: `codex/ariadne-core-orchestration-backends-3`

This batch implements `ARI-MUL-09 / LOC-14` by making the real Codex path a
first-class local demo while preserving the default fake-codex path and all
external-execution gates.

Implemented files:

- `ariadne_ltb/full_demo.py`
- `ariadne_ltb/cli.py`
- `tests/test_v1_codex_teammate.py`
- `README.md`
- `docs/real_codex_smoke_test.md`
- `docs/development_report.md`

Implemented behavior:

- Added `ari demo codex` / `python3.11 -m ariadne_ltb.cli demo codex` as the
  explicit real Codex demo path. It uses the existing `run_full_demo()` and
  `TicketRunOrchestrator`; no duplicate execution pipeline was added.
- Added `--timeout-seconds` to `ari demo` and passed it through the full-demo
  orchestrator path.
- Added `ari backend diagnose codex` to check local Codex command availability,
  `codex exec --help` compatibility, prompt-file support, recommended command
  template, safety-gate env state, and `service_tier` config sanity without
  running a ticket.
- Kept real Codex execution gated by both
  `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1` and `--confirm-execution`.
- Verified that missing gates produce a blocked `ExecutionResult`, blocked
  review, memory, Feishu dry-run plan, next tickets, and board instead of
  falling back to `fake-codex`.
- Updated README and the real Codex smoke-test runbook with `demo codex` and
  `backend diagnose codex`.

Real local Codex run:

- Initial diagnosis found `~/.codex/config.toml` used
  `service_tier = "priority"`, which the local Codex CLI rejects.
- The config was changed outside the repo to `service_tier = "flex"` to match
  the user's cost preference, but the OpenAI provider returned
  `Unsupported service_tier: flex`.
- The config was changed outside the repo to `service_tier = "fast"` for the
  real smoke run.
- With:

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 \
ARIADNE_CODEX_COMMAND_TEMPLATE='codex exec -c model_reasoning_effort="none" --cd {target_repo} - < {handoff_file}' \
python3.11 -m ariadne_ltb.cli --root /tmp/ariadne-loc14-real-fast demo codex --confirm-execution --timeout-seconds 180
```

the real Codex demo passed:

- Backend: `codex`.
- Changed files: `demo_todo/cli.py`, `tests/test_cli.py`.
- Target tests: exit code `0`.
- Reviewer verdict: `pass`.
- Board: `/private/tmp/ariadne-loc14-real-fast/.ariadne/board/index.md`.
- Memory:
  `/private/tmp/ariadne-loc14-real-fast/.ariadne/memory/tickets/ticket_88fbff51677a.md`.
- Feishu dry-run plan:
  `/private/tmp/ariadne-loc14-real-fast/.ariadne/feishu_plans/feishu_1b5b7d988e92.json`.
- Next tickets:
  `/private/tmp/ariadne-loc14-real-fast/.ariadne/artifacts/ticket_88fbff51677a/next_tickets.json`.

Verification:

- `python3.11 -m ruff check ariadne_ltb/cli.py ariadne_ltb/full_demo.py tests/test_v1_codex_teammate.py`:
  passed.
- `python3.11 -m pytest tests/test_v1_codex_teammate.py tests/test_backend_smoke_cli.py tests/test_provider_capability_matrix.py -q`:
  passed, 19 tests.
- `python3.11 -m pytest`: passed, 155 tests.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli --root /tmp/ariadne-loc14-demo demo codex`:
  passed and produced a blocked result with no gate.
- `python3.11 -m ariadne_ltb.cli backend diagnose codex`: passed and reported
  the stdin-compatible template.
- Real gated `demo codex` with `service_tier=fast`: passed with reviewer
  verdict `pass`.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli ticket list`: passed.
- `python3.11 -m ariadne_ltb.cli ticket run ARI-003 --backend fake-codex`:
  passed with reviewer verdict `pass`.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; no secrets were
  printed and external execution remained disabled.
- `python3.11 -m ariadne_ltb.cli backend matrix`: passed.
- `python3.11 -m ariadne_ltb.cli doctor store`: passed with
  `store invariants: ok`, `errors: 0`, and `warnings: 0`.
- `scripts/verify_v1.sh`: exited 0.
- Optional `uv run ari backend diagnose codex`: passed.
- Optional `uv run ari --root /tmp/ariadne-loc14-uv-demo demo codex`: passed
  and produced a blocked result with no gate.
- Optional `uv run ari demo full`: passed.
- Optional `uv run ari ticket list`: passed.
- Optional `uv run ari export board`: passed.
- Optional `uv run ari backend doctor`: passed.

Known limitations:

- `codex exec --help` on this machine does not advertise `--prompt-file`, so
  the recommended real demo template uses stdin redirection.
- `service_tier=flex` was rejected by this provider path even though the local
  CLI config parser accepts it; the documented successful run uses `fast`.
- The real Codex demo is still optional and default-off. The default Ariadne
  demo remains `fake-codex`.

## Core Batch 17: Memory Retrieval Into Planning

Branch: `codex/ariadne-core-orchestration-backends-3`

This batch implements `ARI-MUL-10 / LOC-15` by making local memory searchable
and optionally visible to future planner runs.

Implemented files:

- `ariadne_ltb/memory.py`
- `ariadne_ltb/storage.py`
- `ariadne_ltb/planner.py`
- `ariadne_ltb/cli.py`
- `ariadne_ltb/board.py`
- `tests/test_memory_retrieval_planning.py`
- `README.md`
- `docs/development_report.md`

Implemented behavior:

- Added deterministic local memory search over
  `.ariadne/memory/tickets/*.json`.
- Added `ari memory search <query>` with table output and `--output json`.
- Added `--use-memory` to `ari ingest --planner`, `ari ticket plan`, and
  `ari ticket run`.
- When memory search is enabled, planner output adds memory evidence to the
  `BuildPacket`, including source refs pointing at local memory records and
  artifact refs from the prior run.
- Handoff prompts now include a `Memory Context` section.
- Board output now includes `Planner Memory Evidence` and memory-search status.

Safety boundaries:

- No vector database, network service, hosted backend, Postgres dependency,
  default external execution, Feishu write, auto-commit, auto-push, auto-merge,
  or PR creation was added.
- Memory use is opt-in for planning; default planner behavior remains stable.
- Memory records are treated as local evidence, not higher-priority
  instructions.

Verification:

- `python3.11 -m pytest tests/test_memory_retrieval_planning.py tests/test_v1_planner_quality.py tests/test_true_mvp_product_loop.py::test_deterministic_planner_creates_valid_build_packet_from_arbitrary_markdown -q`:
  passed, 8 tests.
- `python3.11 -m ruff check ariadne_ltb/memory.py ariadne_ltb/planner.py ariadne_ltb/cli.py ariadne_ltb/board.py tests/test_memory_retrieval_planning.py`:
  passed.
- `python3.11 -m pytest`: passed, 158 tests.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli ticket list`: passed.
- `python3.11 -m ariadne_ltb.cli memory search "backend fake-codex review verdict" --output json`:
  passed and returned a local memory hit with capped artifact refs.
- `python3.11 -m ariadne_ltb.cli ticket plan ARI-005 --planner deterministic --use-memory`:
  passed and wrote memory-citing planner artifacts.
- `python3.11 -m ariadne_ltb.cli ticket run ARI-003 --backend fake-codex --use-memory`:
  passed with reviewer verdict `pass`.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; no secrets were
  printed and external execution remained disabled.
- `scripts/verify_v1.sh`: exited 0.

Known limitations:

- Retrieval is lexical keyword matching, not semantic retrieval.
- Memory search ranks local `MemoryRecord` fields only; it cites artifact IDs
  from memory records but does not recursively parse every referenced artifact.
- Memory is opt-in for planning to avoid historical state changing deterministic
  demo behavior unexpectedly.

## Core Roadmap: Multica-Level Local Maturity

Branch: `codex/ariadne-core-orchestration-backends-3`

Added:

- `docs/ops/ARIADNE_MULTICA_MATURITY_ROADMAP.md`

Purpose:

- Capture the current continuation path after the core and frontend branches
  diverged.
- Preserve the current ADR-0004 direction: Ariadne is a local-first
  Ticket-centered Agent Workbench, not a Goal-first planner and not a Multica
  server clone.
- Make the next development step explicit: integrate
  `codex/ariadne-core-orchestration-backends-3` and
  `codex/ariadne-workbench-frontend-lane` before continuing broad feature work.
- Define the remaining work needed to approach Multica-level local maturity:
  resource boundaries, inbox and search, review quality, workdir cleanup, store
  durability, board/web parity, dogfood evidence, and release readiness.

Verification:

- `git diff --check`: passed.

Known limitations:

- This is a planning and handoff document only. It does not implement remaining
  runtime, resource, review, frontend, or release features.
- The document records the current branch reality as of 2026-06-17. Future
  agents must re-check branch state before merging or continuing work.

## Goal Handoff: Ariadne Multica Maturity

Branch: `codex/ariadne-core-orchestration-backends-3`

Added:

- `docs/goals/2026-06-17-2034-ariadne-multica-maturity-goal.md`
- `docs/superpowers/plans/2026-06-17-2034-ariadne-multica-maturity-execution-plan.md`

Purpose:

- Convert `docs/ops/ARIADNE_MULTICA_MATURITY_ROADMAP.md` into a short Codex
  goal that can be used for a long-running goal session.
- Keep the goal under 4000 characters while moving detailed execution steps
  into a separate plan file.
- Preserve the current boundary: do not develop new frontend features in this
  goal, but let Codex decide when the existing frontend/workbench branch should
  be integrated based on branch state, conflicts, and verification.

Verification:

- `git diff --check`: passed.
- Goal file length check: `3220` characters.
- Placeholder scan found only legal Git range syntax in `main...branch`
  commands.

Known limitations:

- This handoff only creates the goal and execution plan. It does not implement
  roadmap phases.
- The timestamped goal records the current branch names. Future executions must
  re-check branch state before editing or merging.

## Production Agent Workbench Roadmap

Branch: `codex/ariadne-core-orchestration-backends-3`

Added:

- `docs/ops/2026-06-17-2043-ARIADNE_PRODUCTION_AGENT_WORKBENCH_ROADMAP.md`
- `docs/goals/2026-06-17-2043-ariadne-production-agent-workbench-goal.md`
- `docs/superpowers/plans/2026-06-17-2043-ariadne-production-agent-workbench-execution-plan.md`

Updated as superseded:

- `docs/ops/ARIADNE_MULTICA_MATURITY_ROADMAP.md`
- `docs/goals/2026-06-17-2034-ariadne-multica-maturity-goal.md`
- `docs/superpowers/plans/2026-06-17-2034-ariadne-multica-maturity-execution-plan.md`

Purpose:

- Shift the roadmap from conservative demo/dry-run maturity to production-first
  agent workbench delivery.
- Make real DeepSeek upstream LLM runtime a P0 product requirement for Build
  Lead, planner, reviewer, knowledge, memory, and integration planning agents.
- Make real Codex and real Claude Code production backends, not only smoke-test
  paths.
- Make gated real Feishu writes and real GitHub integration explicit roadmap
  requirements.
- Keep `fake-codex` only as deterministic test and offline fallback.

Multica reference:

- Multica agents are workspace members bound to a local AI coding tool runtime.
- Multica stores agent instructions, model selection, custom environment
  variables, custom CLI args, MCP config, skills, lifecycle, comments, and
  usage metadata.
- Ariadne should absorb that model for coding runtimes, while adding a
  DeepSeek-backed upstream LLM layer for non-coding agents.

Credential boundary:

- DeepSeek API keys must be supplied through environment or ignored local
  `.env`, never committed.
- Doctor commands may report set/unset but must never print key values.
- Tests must pass without DeepSeek, Codex, Claude, Feishu, GitHub credentials,
  or network access.

Verification:

- `git diff --check`: passed.
- DeepSeek documentation was checked for current OpenAI-compatible base URL and
  model names.
- Local Multica docs and SQL were checked for agent runtime, model,
  `custom_env`, and `custom_args` behavior.

Known limitations:

- This update changes roadmap and execution handoff only. It does not implement
  the real integrations yet.
- The supplied DeepSeek key was intentionally not written to the repository.

## Local DeepSeek Key And Plan Cleanup

Branch: `codex/ariadne-core-orchestration-backends-3`

Local-only configuration:

- Wrote `DEEPSEEK_API_KEY` into ignored local `.env` files for the core worktree
  and the frontend worktree.
- Also wrote `ARIADNE_LLM_PROVIDER=deepseek`,
  `ARIADNE_LLM_MODEL=deepseek-v4-pro`, and
  `ARIADNE_LLM_FAST_MODEL=deepseek-v4-flash`.
- Confirmed `.env` is ignored by git in both worktrees.

Plan cleanup:

- Marked older active planning documents as superseded by the 2043 production
  goal and execution plan:
  - `docs/ops/CODEX_NON_FRONTEND_SECTION_PLAN.md`
  - `docs/ops/CODEX_CORE_SECTION_EXECUTION_PLAN.md`
  - `docs/ops/CODEX_CORE_PARALLEL_EXECUTION_PROTOCOL.md`
  - `docs/superpowers/plans/2026-06-15-ariadne-v1-0-sprint.md`
- Marked the 2043 goal and execution plan as active.

Verification:

- `git check-ignore -v .env .env.local`: confirmed ignored.
- Secret scan over docs found no DeepSeek key.
- `git diff --check`: passed.

Known limitations:

- The local `.env` exists only on this machine and is intentionally untracked.
- Real DeepSeek runtime is not implemented yet; the active plan now makes it the
  first production integration phase.

## 2026-06-17 DeepSeek Upstream LLM Runtime Slice

Branch: `codex/ariadne-core-orchestration-backends-3`

Implemented:

- Replaced the thin DeepSeek wrapper with a typed upstream LLM runtime:
  `LLMRequest`, `LLMResponse`, `LLMError`, `LLMUsage`, injectable transport,
  JSON-mode payloads, timeout configuration, and provider error redaction.
- Added ignored local `.env` loading for a small LLM allowlist so the local
  DeepSeek key can be used without committing credentials.
- Added `ari llm doctor` and safety-gated
  `ari llm smoke --provider deepseek --confirm-external`.
- Added `ariadne_ltb/llm_agents.py` with a minimal JSON LLM agent adapter for
  Build Lead, planner, reviewer, memory, Feishu planner, and GitHub planner
  roles.
- Wired `ari ticket plan --planner llm` through the stronger DeepSeek client.
- Added `ari review run <ticket> --reviewer llm`; LLM review is conservative and
  cannot turn deterministic local failures into a pass.
- Updated README and the active production execution plan.

Safety boundaries:

- No API key values are printed by doctor or smoke commands.
- Automated tests use fake transports and do not require network, DeepSeek,
  Codex, Claude Code, Feishu, or GitHub credentials.
- Real LLM smoke requires the explicit `--confirm-external` gate.

Verification:

- `python3.11 -m pytest tests/test_llm_runtime.py tests/test_llm_agents.py tests/test_v1_planner_quality.py tests/test_true_mvp_product_loop.py::test_llm_planner_missing_key_fails_gracefully`: passed.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m pytest`: 167 passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; secret values redacted.
- `python3.11 -m ariadne_ltb.cli llm doctor`: passed; DeepSeek key reported set without printing the value.
- `scripts/verify_v1.sh`: passed.
- `uv run ari demo full`: passed.
- `uv run ari ticket list`: passed.
- `uv run ari export board`: passed.
- `uv run ari backend doctor`: passed.
- `uv run ari llm doctor`: passed.

Real DeepSeek smoke:

- `python3.11 -m ariadne_ltb.cli llm smoke --provider deepseek --confirm-external`: passed.
- Real planner smoke initially exposed a product issue: the LLM prompt did not
  include the required Build Packet JSON shape, so the provider omitted
  `insight` and Ariadne correctly wrote a blocked planner artifact.
- Fixed the LLM planner prompt to include the complete required JSON shape,
  planning rules, and source evidence snippets.
- `python3.11 -m ariadne_ltb.cli ticket plan ARI-003 --planner llm`: passed
  after the prompt fix.
- `python3.11 -m ariadne_ltb.cli review run ARI-003 --reviewer llm`: passed
  with verdict `pass` after refreshing ARI-003 with a successful local
  execution result.

Known limitations:

- Planner and reviewer now have real DeepSeek-capable paths, but other upstream
  LLM roles still need to be migrated onto `JSONLLMAgent`.
- At this point in the timeline, the full product path still needed real Codex,
  Claude Code, Feishu, and GitHub integration hardening from later phases.
- Local `.ariadne` contains older run history with blocked fake-codex assignment
  records caused by a stale isolated worktree. This is ignored local state; store
  invariants and verification still pass.

## 2026-06-17 Real Codex And Claude Code Production Backend Slice

Branch: `codex/ariadne-core-orchestration-backends-3`

Implemented:

- Promoted Codex and Claude Code execution results to carry first-class provider
  evidence:
  - handoff file path;
  - command template and template env var;
  - provider session id when available;
  - provider failure kind and redacted provider failure evidence.
- Added typed failure reasons for authentication failure, quota exhaustion, and
  invalid provider configuration.
- Added provider failure classification for auth/login/API key, quota/rate
  limit/billing, and invalid service tier/config failures.
- Updated Codex default template to use stdin:
  `codex exec --cd {target_repo} - < {handoff_file}`.
- Updated Claude Code default template to use JSON output:
  `claude --print --output-format json < {handoff_file}`.
- Added command-template placeholders for model, reasoning effort, service tier,
  Claude max turns, and Claude system prompt configuration.
- Added `ari backend diagnose claude-code`.
- Updated provider capability matrix and board output to show stdin/session/model
  support and provider evidence.
- Updated README and the real Codex smoke-test runbook.

Real integration smoke:

- `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 python3.11 -m ariadne_ltb.cli backend smoke-test codex --confirm-execution --timeout-seconds 240`
  initially failed with `Unsupported service_tier: flex`.
- The failure was captured in the execution result with provider failure
  evidence and led to a code change: Ariadne no longer forces `service_tier` in
  the default Codex template.
- Local Codex config was restored to `service_tier=fast` after the provider
  rejected `flex`.
- Re-running the same real Codex smoke test passed:
  - execution result `execution_8737a2ea729f`;
  - exit code `0`;
  - changed files `demo_todo/cli.py`, `tests/test_cli.py`;
  - test exit code `0`;
  - reviewer verdict `pass`;
  - provider session id captured.
- Real Claude Code run also passed:
  - command `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 python3.11 -m ariadne_ltb.cli ticket run ARI-003 --backend claude-code --confirm-execution`;
  - execution result `execution_815fae43c42b`;
  - exit code `0`;
  - changed files `demo_todo/cli.py`, `tests/test_cli.py`;
  - test exit code `0`;
  - reviewer verdict `pass`;
  - provider session id captured.

Verification:

- `python3.11 -m pytest tests/test_real_backend_gates.py tests/test_v1_codex_teammate.py tests/test_true_mvp_product_loop.py tests/test_backend_smoke_cli.py tests/test_provider_capability_matrix.py`: passed.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m pytest`: 172 passed.
- `python3.11 -m ariadne_ltb.cli backend diagnose codex`: passed.
- `python3.11 -m ariadne_ltb.cli backend diagnose claude-code`: passed.

Known limitations:

- Codex `flex` service tier is not currently usable with the local/provider
  combination tested here; Ariadne records that as provider configuration
  evidence instead of assuming it works.
- At this point in the timeline, real Feishu and GitHub integration phases were
  still pending; later sections document their implementation slices.

## 2026-06-17 Real Feishu Write Gate Slice

Branch: `codex/ariadne-core-orchestration-backends-3`

Implemented:

- Added first-class Feishu write-back commands:
  - `ari feishu plan <ticket>`;
  - `FEISHU_ENABLE_WRITE=1 ari feishu write <ticket> --confirm-write`.
- Kept the existing dry-run Feishu plan as the preview path.
- Added a real gated `lark-cli docs +create` write path.
- Added `FeishuWriteResult` with:
  - ticket and plan ids;
  - blocked/ok state;
  - typed failure reason;
  - redacted command, stdout, and stderr;
  - content path;
  - document id and document URL when returned by `lark-cli`;
  - operation summary.
- Persisted Feishu integration evidence under:
  `.ariadne/integrations/feishu/<ticket_key>/<result_id>.json`.
- Updated the board to show the latest real Feishu write result under the
  Feishu section.
- Added deterministic tests for missing confirmation, disabled write gate,
  missing `lark-cli`, mocked successful write, result persistence, and secret
  redaction.
- Updated README and the active production execution plan.

Real integration smoke:

- Local `lark-cli` was found at `/opt/homebrew/bin/lark-cli`.
- Real Feishu write was not attempted because `FEISHU_ENABLE_WRITE` was not
  enabled in the current environment.
- Gated write refusal was exercised with:
  `python3.11 -m ariadne_ltb.cli feishu write ARI-003 --confirm-write`.
- The command returned Ariadne exit code `2` and wrote a blocked result:
  `.ariadne/integrations/feishu/ARI-003/feishu_write_05bcaf270128.json`.

Safety boundaries:

- Real writes require both `FEISHU_ENABLE_WRITE=1` and `--confirm-write`.
- Tests do not require Feishu credentials or network access.
- Feishu token, secret, key, and bearer-like values are redacted before being
  stored in result JSON or printed.

Verification:

- `python3.11 -m pytest tests/test_feishu_real_write_gate.py`: passed.
- `python3.11 -m pytest tests/test_feishu_real_write_gate.py tests/test_true_mvp_product_loop.py tests/test_v1_doctor_release.py`: passed.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m pytest`: 178 passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; secret values redacted.
- `scripts/verify_v1.sh`: passed.
- `uv run ari demo full`: passed.
- `uv run ari ticket list`: passed.
- `uv run ari export board`: passed.
- `uv run ari backend doctor`: passed.
- `uv run ari feishu plan ARI-003`: passed.

Known limitations:

- The write adapter currently creates one Markdown Docx document from the
  existing Feishu write plan; richer routing to Feishu docs/tasks/base records
  remains future work.
- A full successful real Feishu write still requires the user environment to
  enable `FEISHU_ENABLE_WRITE=1` and have `lark-cli` authenticated.
- Real GitHub integration was completed in the following implementation slice.

## 2026-06-17 Real GitHub Integration Slice

Branch: `codex/ariadne-core-orchestration-backends-3`

Implemented:

- Added first-class GitHub commands:
  - `ari github doctor`;
  - `ari github link <ticket> --repo <owner/name> --issue <number> [--pr <number>] [--branch <branch>]`;
  - `ari github sync <ticket> --confirm-write`.
- Added `GitHubIntegrationResult` to record:
  - operation;
  - ok/blocked state;
  - typed failure reason;
  - repo, issue, PR, branch, commit SHA, remote URL, and comment URL;
  - redacted command summaries, stdout, stderr, and provider evidence.
- Persisted GitHub evidence under:
  `.ariadne/integrations/github/<ticket_key>/<result_id>.json`.
- Implemented `gh`-based doctor, issue read, PR read, and issue comment sync.
- GitHub remote writes are blocked unless `--confirm-write` is provided.
- Updated board output to show the latest GitHub integration result.
- Added deterministic tests for doctor token safety, local link metadata,
  missing confirmation, missing `gh`, mocked successful sync, and token
  redaction.
- Updated README and the active production execution plan.

Real integration smoke:

- Local `gh` was found at `/opt/homebrew/bin/gh`.
- `gh auth status` reported an authenticated `Hackerismydream` account with the
  token value masked by `gh`.
- A real GitHub remote write was not attempted in this slice because no safe
  target issue for a real Ariadne sync comment was specified. Ariadne now has
  the gated path; writing to a real issue should be done only against an
  explicitly selected ticket/issue link.

Safety boundaries:

- `GITHUB_TOKEN` is read only from environment and is never printed.
- `ghp_`, `gho_`, token, secret, key, authorization, and bearer-like values are
  redacted from persisted results.
- `github link` is local metadata only.
- `github sync` is the only remote-write path and requires `--confirm-write`.
- Ariadne still does not merge, auto-merge, delete branches, or create PRs in
  this slice.

Verification:

- `python3.11 -m pytest tests/test_github_integration.py`: passed.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m pytest`: 183 passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; secret values redacted.
- `python3.11 -m ariadne_ltb.cli github doctor`: passed; `gh auth status` ok.
- `python3.11 -m ariadne_ltb.cli github link ARI-003 --repo Hackerismydream/Ariadne --issue 123 --branch codex/ariadne-core-orchestration-backends-3`: passed locally and wrote a link result.
- `python3.11 -m ariadne_ltb.cli github sync ARI-003`: returned exit code `2` as expected and wrote a blocked result because `--confirm-write` was not provided.
- `scripts/verify_v1.sh`: passed.
- `uv run ari demo full`: passed.
- `uv run ari ticket list`: passed.
- `uv run ari export board`: passed.
- `uv run ari backend doctor`: passed.
- `uv run ari github doctor`: passed.

Known limitations:

- GitHub sync currently posts an issue comment for a linked ticket; richer PR
  status/check synchronization and issue creation are still future work.
- Successful real remote write still requires an explicitly selected safe issue
  target.

## 2026-06-17 Inbox Search Recovery Slice

Branch: `codex/ariadne-core-orchestration-backends-3`

Implemented:

- Added `InboxItem` domain model with severity, status, typed failure reason,
  evidence ref, and recommended action.
- Added `.ariadne/inbox/items.json` persistence through `AriadneStore`.
- Added `ariadne_ltb/inbox.py` to materialize blocked assignments, failed or
  blocked execution results, Feishu write failures, and GitHub integration
  failures into local inbox items.
- Added `ari inbox refresh` and `ari inbox list --refresh --output json`.
- Added `ariadne_ltb/local_search.py` and top-level `ari search` for local
  lexical evidence search.
- Search indexes tickets, comments, artifacts, memory records, reviews,
  execution results, inbox items, Feishu write results, and GitHub integration
  results.
- Updated the board system summary to show inbox count and latest inbox items.
- Updated README and the active production execution plan.

Real integration smoke:

- No new real external write was attempted in this slice.
- The slice uses persisted failure evidence from assignments, execution,
  Feishu, and GitHub results; automated tests use deterministic local model
  objects and monkeypatched command discovery.

Safety boundaries:

- Inbox and search are local-only and do not require network, Codex, Claude,
  DeepSeek, Feishu, GitHub, or credentials.
- Search reads persisted Ariadne evidence and artifact text; it does not send
  content to an external service.
- Inbox materialization records failure summaries and evidence paths but does
  not rerun or mutate external integrations.

Verification:

- `python3.11 -m ruff check .`: passed.
- `python3.11 -m pytest tests/test_inbox.py tests/test_local_search.py`:
  passed.
- `python3.11 -m pytest`: 187 passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local `.env`
  finding was redacted.
- `python3.11 -m ariadne_ltb.cli inbox refresh`: passed and wrote 29 local
  inbox items in the current dogfood store.
- `python3.11 -m ariadne_ltb.cli inbox list --output json`: passed.
- `python3.11 -m ariadne_ltb.cli search "isolated worktree" --output json
  --limit 5`: passed.
- `scripts/verify_v1.sh`: passed.

Known limitations:

- Inbox severity currently maps to a small high/medium set; richer ownership,
  snooze, and recovery workflow states remain future work.
- Search is lexical and local; ranking is intentionally simple until retrieval
  requirements harden around real dogfood evidence.

## 2026-06-17 Review Eval Acceptance Evidence Slice

Branch: `codex/ariadne-core-orchestration-backends-3`

Implemented:

- Extended `ReviewReport` with reviewer mode, risk score,
  acceptance-criterion coverage, evidence refs, and next-ticket suggestions.
- Updated deterministic reviewer output to score risk from verdict, failed
  checks, warnings, failure reasons, and uncovered acceptance criteria.
- Updated LLM reviewer output to preserve deterministic baseline evidence and
  mark missing-key LLM reviews as `llm_blocked` with high risk.
- Updated `ari ticket review` and `ari review run` to print risk score and
  acceptance coverage.
- Updated the board review section to show reviewer mode, risk score,
  acceptance coverage, evidence refs, and review next-ticket suggestions.
- Added deterministic tests for passing review evidence, blocked review risk,
  and missing-key LLM reviewer evidence preservation.
- Updated README and the active production execution plan.

Real integration smoke:

- No new real LLM call was attempted in this slice. LLM reviewer integration
  remains available through `ari review run <ticket> --reviewer llm`; tests use
  missing-key and fake-transport paths so they do not require network.

Safety boundaries:

- Review scoring is local and deterministic unless the user explicitly selects
  `--reviewer llm`.
- Missing DeepSeek configuration produces a blocked review report instead of
  silently falling back to deterministic success.

Verification:

- `python3.11 -m ruff check .`: passed.
- `python3.11 -m pytest tests/test_review_risk_scoring.py
  tests/test_llm_runtime.py tests/test_true_mvp_product_loop.py`: passed.
- `python3.11 -m pytest`: 190 passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local `.env`
  finding was redacted.
- `python3.11 -m ariadne_ltb.cli review run ARI-003`: passed and printed
  reviewer mode, verdict, risk score, and acceptance coverage.
- `scripts/verify_v1.sh`: passed.

Known limitations:

- Risk scoring is intentionally simple and conservative; it is not yet calibrated
  against a production corpus of real agent runs.
- Next-ticket suggestions are review-local hints; full ticket generation still
  happens through the existing next-ticket/backlog path.

## 2026-06-17 Store Workdir Release Evidence Slice

Branch: `codex/ariadne-core-orchestration-backends-3`

Implemented:

- Added `ReleaseEvidencePacket` to summarize current release evidence from the
  local Ariadne store.
- Added `.ariadne/evidence/release_evidence_packet.json` persistence through
  `AriadneStore`.
- Added `ariadne_ltb/evidence.py` and `ari evidence packet`.
- Added `WorkdirStatus`, `WorkdirCleanupResult`, `ariadne_ltb/workdir_policy.py`,
  `ari workdir list`, and `ari workdir cleanup --confirm-cleanup`.
- Workdir cleanup only targets Ariadne-managed paths under `.ariadne/worktrees`.
- Dirty generated workdirs are skipped unless `--force-dirty` is explicit.
- Cleanup also deletes Ariadne-generated local branches such as
  `ariadne/ari-003-ticket88`, preventing repeated verification from blocking on
  stale branch names after the worktree directory is gone.
- Updated `scripts/verify_v1.sh` to clean generated workdirs before and after
  the daemon verification path, then generate a release evidence packet.
- Added deterministic tests for release evidence packet generation, machine
  readable CLI output, workdir listing, cleanup confirmation gating, and dirty
  generated workdir force cleanup.
- Updated README and the active production execution plan.

Real integration smoke:

- No new real external provider call was attempted in this slice.
- Current dogfood evidence packet recorded local Codex and Claude CLI
  availability, external execution gate disabled, DeepSeek key set, and local
  `.env` redacted by secret scan.

Safety boundaries:

- `ari workdir cleanup` requires `--confirm-cleanup`.
- Cleanup is scoped to `.ariadne/worktrees` and refuses paths outside the
  Ariadne-managed workdir root.
- Branch cleanup is limited to branch names starting with `ariadne/`.
- Dirty workdirs are preserved by default; `--force-dirty` is explicit and used
  by `scripts/verify_v1.sh` only for generated verification cleanup.
- `ari evidence packet` is local-only and does not call external services.

Verification so far:

- `python3.11 -m ruff check .`: passed.
- `python3.11 -m pytest tests/test_workdir_policy.py
  tests/test_release_evidence.py tests/test_worktree_isolation.py
  tests/test_store_doctor.py`: passed.
- `python3.11 -m pytest`: 196 passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local `.env`
  finding was redacted.
- `python3.11 -m ariadne_ltb.cli workdir list --output json`: passed.
- `python3.11 -m ariadne_ltb.cli evidence packet --output json`: passed and
  wrote `.ariadne/evidence/release_evidence_packet.json`.
- `scripts/verify_v1.sh`: passed. The script removed stale generated workdirs
  and deleted `ariadne/ari-003-ticket88`, then the daemon assignment completed
  successfully and final cleanup removed the generated dirty workdir and branch.

Known limitations:

- Release evidence is a local JSON packet, not yet a signed or immutable release
  attestation.
- Workdir cleanup does not delete assignment history; it only removes generated
  workdirs and marks worktree isolation records inactive.

## 2026-06-17 Product Dogfood Slice

Branch: `codex/ariadne-core-orchestration-backends-3`

Implemented / fixed:

- Fixed the Feishu `lark-cli` adapter to run from the integration workspace and
  pass `--content @<relative-file>` instead of an absolute path. The real
  `lark-cli` rejected absolute `@file` paths.
- Updated Feishu tests to assert the subprocess cwd and relative content path.
- Added `ari github create-issue <ticket> --confirm-write` so Ariadne can create
  a controlled GitHub issue from a local ticket before running sync comments.
- Ran real DeepSeek, Codex, Claude Code, and Feishu dogfood paths.
- Ran real GitHub issue creation and sync comment dogfood paths.
- Regenerated release evidence packet and board after real dogfood runs.

Real integration results:

- `python3.11 -m ariadne_ltb.cli llm doctor`: passed; DeepSeek key reported as
  set without printing the value.
- `python3.11 -m ariadne_ltb.cli llm smoke --provider deepseek
  --confirm-external`: passed with real DeepSeek API; model `deepseek-v4-pro`;
  usage total tokens `147`.
- `python3.11 -m ariadne_ltb.cli backend diagnose codex`: passed; local Codex
  CLI found at `/opt/homebrew/bin/codex`.
- `python3.11 -m ariadne_ltb.cli backend diagnose claude-code`: passed; local
  Claude CLI found at `/opt/homebrew/bin/claude`.
- First real Codex smoke attempt failed with execution
  `execution_c6bde67efd51` because the local Codex provider rejected
  `service_tier=flex` with `Unsupported service_tier: flex`.
- Local Codex config was reverted to `service_tier=fast` because the real
  provider rejected `flex` in this environment.
- Second real Codex smoke passed with execution `execution_52c4c7349868`:
  exit code `0`, test exit code `0`, changed files `demo_todo/cli.py` and
  `tests/test_cli.py`, provider session `019ed5e8-c434-75b0-8ac1-4bc403144b70`,
  reviewer verdict `pass`.
- Real Claude Code run passed with execution `execution_ace5b5b8d093`: exit
  code `0`, test exit code `0`, changed files `demo_todo/cli.py` and
  `tests/test_cli.py`, provider session `95689d7e-81b7-44c6-873c-0359fea12669`,
  reviewer verdict `pass`.
- First real Feishu write failed with result `feishu_write_73f39fe21d34`
  because `lark-cli` requires `@file` paths to be relative to cwd.
- After the adapter fix, real Feishu write passed with result
  `feishu_write_92be55ff82ce` and document URL
  `https://icnoljnkix43.feishu.cn/docx/KqOldcuIoomZZ6xDJhgcrNIdnFc`.
- `python3.11 -m ariadne_ltb.cli github doctor`: passed; `gh auth status` is
  ok for repo `Hackerismydream/Ariadne`.
- `python3.11 -m ariadne_ltb.cli github create-issue ARI-003 --repo
  Hackerismydream/Ariadne --branch codex/ariadne-core-orchestration-backends-3
  --confirm-write`: passed and created issue #8 at
  `https://github.com/Hackerismydream/Ariadne/issues/8`.
- `python3.11 -m ariadne_ltb.cli github sync ARI-003 --confirm-write`: passed
  and posted sync comment
  `https://github.com/Hackerismydream/Ariadne/issues/8#issuecomment-4731296757`.

Safety boundaries:

- Real Codex and Claude execution used
  `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1` plus `--confirm-execution`.
- Real Feishu write used `FEISHU_ENABLE_WRITE=1` plus `--confirm-write`.
- No Ariadne runtime path committed, pushed, merged, created a PR, or auto-merged.
- Real coding changes were confined to the generated demo target project under
  `.ariadne/demo_target_project`.
- Secret scans continued to redact the local `.env` finding.

Verification so far:

- `python3.11 -m ruff check .`: passed.
- `python3.11 -m pytest`: passed, `198 passed`.
- `python3.11 -m pytest tests/test_feishu_real_write_gate.py
  tests/test_github_integration.py`: passed, `12 passed`.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; it reports local
  `.env` as a blocked/redacted secret finding.
- `scripts/verify_v1.sh`: passed; final release evidence packet
  `release_evidence_1f63a56049f0` reports store invariants ok, active workdirs
  `0`, dirty workdirs `0`.
- `python3.11 -m ariadne_ltb.cli evidence packet`: passed after real dogfood.
- `git grep` for DeepSeek, GitHub, and Feishu secret patterns found only
  placeholders in `.env.example` and archived workpack docs, not real secrets.

Known limitations:

- Codex `service_tier=flex` is not usable in this current provider environment;
  real Codex success currently requires `service_tier=fast`.
- GitHub PR/status write paths are still narrower than the full roadmap: this
  slice proves issue creation and comment sync, while PR creation/check-status
  automation remains a follow-up.

## 2026-06-17 Workbench Frontend Safe Integration Slice

Branch: `codex/ariadne-production-frontend-integration`

Implemented / integrated:

- Started from the verified core branch
  `codex/ariadne-core-orchestration-backends-3` at commit `1956e5e`.
- Safely restored only the frontend lane assets instead of merging the whole
  older frontend branch, because a direct branch merge would delete many newer
  backend modules and tests.
- Added the standalone React/Vite workbench under
  `frontend/ariadne-workbench/`.
- Preserved the Multica-inspired app shell, issue board, goal page, agent page,
  runtime page, skill page, inbox page, and floating agent dock.
- Reworked `frontend/ariadne-workbench/scripts/sync-local-data.mjs` into a
  read-only Ariadne adapter that consumes:
  - `.ariadne/tickets/*.json`;
  - `.ariadne/artifacts/<ticket>/build_packet.json`;
  - `.ariadne/artifacts/<ticket>/review_report.json`;
  - `.ariadne/artifacts/<ticket>/changed_files.json`;
  - `.ariadne/artifacts/<ticket>/next_tickets.json`;
  - `.ariadne/inbox/items.json`;
  - `.ariadne/journal/events.jsonl`;
  - `.ariadne/comments/*.jsonl`;
  - `.ariadne/evidence/release_evidence_packet.json`;
  - `.ariadne/runtimes/capability_snapshot.json`;
  - `.ariadne/project/resources.json`;
  - `.ariadne/integrations/feishu/*/*.json`;
  - `.ariadne/integrations/github/*/*.json`.
- Added frontend-local ignore rules for `node_modules/`, `dist/`,
  `public/web_data/`, and TypeScript build info so machine-local snapshots are
  not committed.
- Updated README with frontend run/build/sync instructions.

Verification:

- `npm run sync:data`: passed and generated a local workbench snapshot with
  `8` tickets, `5` runtimes, and `16` inbox items.
- `npm install`: passed with `0` vulnerabilities reported by npm.
- `npm run typecheck`: passed.
- `npm run build`: passed; Vite produced static assets under
  `frontend/ariadne-workbench/dist/`.
- `npm run dev -- --port 5177`: started locally; `curl
  http://127.0.0.1:5177/` returned the Vite HTML shell and
  `curl http://127.0.0.1:5177/web_data/workbench.json` returned
  `Ariadne Production Agent Workbench`, `8` tickets, `5` runtimes, and `16`
  inbox items. The dev server was stopped after verification.

Safety boundaries:

- The frontend is read-only and does not mutate `.ariadne` state.
- The generated `public/web_data/workbench.json` is ignored because it contains
  local filesystem paths.
- This integration did not merge the old frontend branch wholesale and did not
  remove any newer backend production integration files.

Known limitations:

- The frontend still uses a static generated JSON snapshot, not a live Ariadne
  API or WebSocket stream.
- Mutating actions such as assigning tickets, launching real Codex/Claude runs,
  Feishu writes, and GitHub writes remain CLI-only and gated.
- Browser-level interaction QA has not yet been run on this integration branch;
  this slice verified static build plus HTTP availability.

## 2026-06-17 GitHub PR And Status Integration Slice

Branch: `codex/ariadne-production-frontend-integration`

Implemented:

- Added gated PR creation:
  `ari github create-pr <ticket> --base <branch> --head <branch>
  --confirm-write`.
- Added read-only GitHub status capture:
  `ari github status <ticket>`.
- `create-pr` writes a PR body file under
  `.ariadne/integrations/github/<ticket>/`, uses `gh pr create`, parses the PR
  URL, records the PR number, and links it back into local ticket metadata.
- `status` reads linked issue, PR, branch, mergeability/review/check evidence
  through `gh issue view`, `gh pr view`, and `gh pr checks`.
- `gh pr checks` exit code `8` is treated as a successful status capture with
  pending checks, not as a failed integration.
- `gh pr checks` output containing `no checks reported` is treated as a
  successful status capture with an empty check list, not as a failed
  integration.
- Added deterministic tests for missing confirmation, successful PR creation,
  secret redaction, status capture, pending checks, and no-checks branches.

Verification so far:

- `python3.11 -m pytest tests/test_github_integration.py`: passed, `11 passed`.
- `python3.11 -m ruff check ariadne_ltb/github_integration.py
  ariadne_ltb/cli.py tests/test_github_integration.py`: passed.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m pytest`: passed, `202 passed`.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local `.env` is
  reported as a redacted blocked secret finding.
- `scripts/verify_v1.sh`: passed; final release evidence packet
  `release_evidence_0c426f1aa231` reports store invariants ok, active workdirs
  `0`, dirty workdirs `0`.
- `npm run sync:data`: passed and generated a frontend snapshot with `8`
  tickets, `5` runtimes, and `18` inbox items.
- `npm run typecheck`: passed.
- `npm run build`: passed.

Real integration status:

- `python3.11 -m ariadne_ltb.cli github link ARI-003 --repo
  Hackerismydream/Ariadne --issue 8 --branch
  codex/ariadne-production-frontend-integration`: passed locally.
- `python3.11 -m ariadne_ltb.cli github create-pr ARI-003 --repo
  Hackerismydream/Ariadne --base main --head
  codex/ariadne-production-frontend-integration --confirm-write`: passed and
  created PR #9 at `https://github.com/Hackerismydream/Ariadne/pull/9`.
- First real `github status` read exposed a product bug: `gh pr checks` returns
  non-zero when there are no checks reported on the branch.
- After the no-checks fix, `python3.11 -m ariadne_ltb.cli github status
  ARI-003`: passed and recorded issue #8, PR #9, branch
  `codex/ariadne-production-frontend-integration`, and an empty check list as
  valid status evidence.

## 2026-06-17 22:42 CST GitHub Evidence Visibility Slice

Branch: `codex/ariadne-production-frontend-integration`

Implemented:

- Re-checked the production integration branch against the separate frontend
  lane. A direct merge would have brought older core/runtime changes from the
  frontend branch history, so the merge was aborted and only the safe frontend
  generated-data ignore rule was kept.
- Extended the Markdown board GitHub section to show PR status evidence:
  issue state, PR state, base/head branch, mergeability, review decision,
  checks status, check counts, and recent GitHub operations.
- Extended the read-only frontend workbench data contract with per-ticket
  GitHub evidence.
- Updated the frontend sync script to aggregate
  `.ariadne/integrations/github/<ticket>/*.json` into each ticket.
- Added a GitHub panel in the ticket inspector showing issue/PR links, branch,
  commit, checks, mergeability, review decision, and recent GitHub operation
  history.
- Added deterministic board coverage for `checks_status=no_checks_reported`.
- Fixed a reviewer finding where `state=completed` was incorrectly treated as
  a passing GitHub check. Check counts now prefer `bucket`, then `conclusion`,
  and only use state/status for pending detection.

Verification:

- `python3.11 -m pytest tests/test_v1_board_ux.py -q`: passed, `5 passed`.
- `python3.11 -m pytest`: passed, `204 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed and the board includes
  `Checks status: no_checks_reported` and `Checks summary`.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local `.env` is
  reported as a redacted secret-scan finding.
- `scripts/verify_v1.sh`: passed and generated release evidence packet
  `release_evidence_846f049d3807`.
- `cd frontend/ariadne-workbench && npm run sync:data`: passed and generated a
  local ignored `web_data/workbench.json` snapshot with `8` tickets, `5`
  runtimes, and `18` inbox items.
- `cd frontend/ariadne-workbench && npm run typecheck`: passed.
- `cd frontend/ariadne-workbench && npm run build`: passed.
- Secret grep: no real DeepSeek, GitHub, or Feishu token found in tracked
  source/docs/test/frontend paths; only placeholder `FEISHU_APP_SECRET=` docs
  remain.

Safety boundaries:

- This slice did not perform new GitHub writes and did not claim a new real
  GitHub run. It surfaces the previously recorded issue #8 / PR #9 status
  evidence.
- The frontend remains read-only.
- `frontend/ariadne-workbench/public/web_data/*.json` is ignored because it is
  a generated local snapshot and can contain local filesystem paths.
