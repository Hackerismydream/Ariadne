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

## 2026-06-17 23:05 CST Integration Doctor Slice

Branch: `codex/ariadne-production-frontend-integration`

Implemented:

- Added the roadmap acceptance command `ari doctor integrations`.
- The command aggregates local readiness for DeepSeek, Codex, Claude Code,
  Feishu/lark-cli, GitHub/gh, and required safety gates.
- The command persists a local machine-readable snapshot at
  `.ariadne/doctor/integrations.json` for release evidence and workbench use.
- Added `--json` output for automation.
- Added `doctor integrations` to `scripts/verify_v1.sh` so release readiness
  now verifies the integration surface, not only the deterministic demo path.

Safety boundaries:

- The command does not perform external writes.
- It prints only set/unset and command availability, never secret values.
- LLM base URL values are reduced to URL origin before printing or persisting,
  so userinfo, paths, and query tokens from proxy URLs are not exposed.
- `gh auth status` is used only as a local auth readiness check; no GitHub
  mutation is performed.
- In `scripts/verify_v1.sh`, `doctor integrations` is a report-only readiness
  smoke. It records missing auth/gates as evidence instead of failing the whole
  deterministic release script.

Local result observed:

- DeepSeek API key: set.
- Codex CLI: found at `/opt/homebrew/bin/codex`.
- Claude Code CLI: found at `/opt/homebrew/bin/claude`.
- lark-cli: found at `/opt/homebrew/bin/lark-cli`.
- gh CLI: found at `/opt/homebrew/bin/gh`.
- GitHub auth status: ok.
- External execution and Feishu write gates: unset, as expected unless a real
  confirmed run is being performed.

Verification:

- `python3.11 -m pytest tests/test_v1_doctor_release.py -q`: passed,
  `6 passed`.
- `python3.11 -m pytest`: passed, `206 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local `.env` is
  reported as a redacted secret-scan finding.
- `python3.11 -m ruff check ariadne_ltb/doctor.py ariadne_ltb/cli.py
  tests/test_v1_doctor_release.py`: passed.
- `python3.11 -m ariadne_ltb.cli doctor integrations`: passed.
- `python3.11 -m ariadne_ltb.cli doctor integrations --json | python3.11 -m
  json.tool`: passed.
- `scripts/verify_v1.sh`: passed and now includes `doctor integrations`; release
  evidence packet generated as `release_evidence_3a2c34bc7edb`.
- Secret grep found no real DeepSeek, GitHub, or Feishu token in tracked code,
  docs, tests, frontend, or scripts; only placeholder references remain.

## 2026-06-17 23:25 CST GitHub Transport Doctor Slice

Branch: `codex/ariadne-production-frontend-integration`

Why this slice exists:

- During the integration doctor push, `gh auth status` was healthy but local
  `git push` still failed or hung because git transport was using a broken
  proxy / credential path.
- That is a real production-readiness gap: Ariadne must distinguish GitHub API
  authentication from local git transport readiness.

Implemented:

- `ari github doctor` now runs a read-only git transport probe with
  `git ls-remote --heads origin <current-branch>`.
- The probe uses `GIT_TERMINAL_PROMPT=0` and a short timeout so doctor commands
  do not hang on broken credential helpers.
- The probe reports branch, transport status, configured git proxies, and a
  redacted first-line evidence string.
- `ari doctor integrations` now persists the same GitHub git transport snapshot
  under `.ariadne/doctor/integrations.json`.

Safety boundaries:

- The transport probe is read-only.
- Proxy URLs are redacted if they contain username/password userinfo.
- GitHub tokens and environment secrets are still reported only as set/unset.

Local result observed:

- GitHub API auth is healthy after `gh auth login`.
- The previous direct `git push` path exposed a local transport/proxy problem;
  this slice makes that class of failure visible through Ariadne doctor output.

Verification:

- `python3.11 -m pytest tests/test_github_integration.py
  tests/test_v1_doctor_release.py -q`: passed, `18 passed`.
- `python3.11 -m pytest`: passed, `207 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local `.env` is
  reported as a redacted secret-scan finding.
- `python3.11 -m ariadne_ltb.cli github doctor`: passed and now reports
  `git transport status: ok` locally.
- `python3.11 -m ariadne_ltb.cli doctor integrations`: passed and now includes
  GitHub git transport status.
- `scripts/verify_v1.sh`: passed; release evidence packet generated as
  `release_evidence_b17915af9789`.

## 2026-06-17 23:40 CST Release Evidence Integration References Slice

Branch: `codex/ariadne-production-frontend-integration`

Why this slice exists:

- The production roadmap requires board and evidence packets to show real
  integration evidence.
- Before this slice, `ari evidence packet` summarized core store/board state but
  did not directly reference the integration doctor snapshot or Feishu/GitHub
  integration evidence directories.

Implemented:

- `ari evidence packet` now generates the integration doctor snapshot as part of
  packet generation.
- Release evidence refs now include:
  - `.ariadne/doctor/integrations.json`;
  - `.ariadne/runtimes/capability_snapshot.json`;
  - `.ariadne/integrations/feishu/`;
  - `.ariadne/integrations/github/`.

Safety boundaries:

- The integration doctor snapshot is read-only with respect to external
  services. It records readiness and local transport evidence but does not write
  to Feishu or GitHub.
- Secret values remain redacted; the release packet only stores local paths and
  set/unset readiness evidence.

Verification:

- `python3.11 -m pytest tests/test_release_evidence.py -q`: passed, `2 passed`.
- `python3.11 -m pytest`: passed, `207 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local `.env` is
  reported as a redacted secret-scan finding.
- `python3.11 -m ariadne_ltb.cli doctor integrations`: passed.
- `python3.11 -m ariadne_ltb.cli evidence packet --output json`: passed and
  includes integration doctor, runtime capabilities, Feishu integration, and
  GitHub integration refs.
- `scripts/verify_v1.sh`: passed; release evidence packet generated as
  `release_evidence_0491ee3622e7`.

## 2026-06-17 23:55 CST Product Readiness Doctor Slice

Branch: `codex/ariadne-production-frontend-integration`

Why this slice exists:

- `ari doctor integrations` reports raw integration readiness, and
  `ari evidence packet` records evidence, but users still needed one command
  that maps the production roadmap acceptance path to concrete ready / blocked /
  action-required checks.
- README still presented `fake-codex` as the recommended product path, which
  conflicted with the production-first roadmap. This slice moves fake-codex back
  to deterministic offline fallback positioning.

Implemented:

- Added `ari doctor product`.
- Added `ari doctor product --json`.
- The command writes `.ariadne/doctor/product_readiness.json`.
- The readiness snapshot checks:
  - DeepSeek key presence;
  - Codex CLI availability;
  - Claude Code CLI availability;
  - external execution gate state;
  - Feishu write gate state;
  - lark-cli availability;
  - GitHub CLI auth;
  - GitHub git transport;
  - release evidence packet presence;
  - integration refs inside the release evidence packet.
- Added `ari doctor product` to `scripts/verify_v1.sh`.
- Updated README to show the real gated production product path first and the
  `fake-codex` path only as deterministic offline fallback.

Safety boundaries:

- `ari doctor product` performs no external writes.
- Execution and Feishu gates are reported as `action_required` when unset, not
  treated as a test failure.
- Secret values remain redacted; JSON output contains only set/unset, statuses,
  local paths, and next-action text.

Verification:

- `python3.11 -m pytest tests/test_v1_doctor_release.py -q`: passed,
  `7 passed`.
- `python3.11 -m pytest`: passed, `208 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local `.env` is
  reported as a redacted secret-scan finding.
- `python3.11 -m ariadne_ltb.cli doctor integrations`: passed.
- `python3.11 -m ariadne_ltb.cli doctor product`: passed and reports
  `Product readiness: action_required`.
- `scripts/verify_v1.sh`: passed; release evidence packet generated as
  `release_evidence_d6b60f5ba572`.

Current readiness interpretation:

- DeepSeek, CodexBackend, ClaudeCodeBackend, lark-cli, GitHub CLI auth, and
  GitHub git transport are locally detectable.
- The product readiness result is still `action_required` because the real
  external execution and Feishu write gates are intentionally unset outside a
  confirmed write/execution command.

## 2026-06-18 00:05 CST Product Readiness Real Evidence Slice

Branch: `codex/ariadne-production-frontend-integration`

Why this slice exists:

- The first product doctor slice checked integration availability and release
  packet references, but it could still overstate readiness by only proving that
  local commands and credentials were detectable.
- The production roadmap needs a stronger distinction between "tools are
  available" and "the real product path has already produced successful
  evidence."

Implemented:

- `ari doctor product` now checks recorded real-success evidence for:
  - CodexBackend execution with exit code 0 and test exit code 0;
  - ClaudeCodeBackend execution with exit code 0 and test exit code 0;
  - Feishu write result with a real document reference;
  - GitHub write result from create issue, create PR, or sync.
- Missing real-success evidence is reported as `action_required`.
- Existing failed real evidence is summarized as `blocked` unless a later
  success exists.
- Failure summaries are redacted and truncated before being written into
  `.ariadne/doctor/product_readiness.json`.

Safety boundaries:

- The command still performs no external writes.
- The new evidence checks read only local Ariadne JSON artifacts under
  `.ariadne/`.
- Secret values and large provider stderr bodies are not copied into the
  readiness summary.

Verification so far:

- `python3.11 -m pytest tests/test_v1_doctor_release.py -q`: passed,
  `8 passed`.
- `python3.11 -m pytest`: passed, `209 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ruff check ariadne_ltb/doctor.py tests/test_v1_doctor_release.py`:
  passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local `.env` is
  reported as a redacted secret-scan finding.
- `python3.11 -m ariadne_ltb.cli doctor integrations`: passed.
- `python3.11 -m ariadne_ltb.cli doctor product`: passed and reports real
  Codex, Claude Code, Feishu, and GitHub evidence as `ready`; overall status is
  still `action_required` because write/execution gates are intentionally unset.
- `scripts/verify_v1.sh`: passed; release evidence packet generated as
  `release_evidence_5d35cc75fdf7`.

## 2026-06-18 00:20 CST Release Evidence Product Readiness Slice

Branch: `codex/ariadne-production-frontend-integration`

Branch integration decision:

- Rechecked the core worktree and frontend lane. Both were clean.
- Directly merging `codex/ariadne-workbench-frontend-lane` is deferred because
  that branch diverged from `main` before the current production backend work
  and would delete or roll back many current backend modules and tests.
- The latest frontend-only commit can be cherry-picked later, but the safer
  production move for this slice was to harden the backend evidence contract
  first.

Why this slice exists:

- `ari doctor product` had the strongest readiness view, but
  `ari evidence packet` still only referenced integration directories and did
  not embed the product readiness result itself.
- Release evidence should be sufficient for an AI builder or reviewer to tell
  whether Ariadne has real Codex, Claude Code, Feishu, and GitHub success
  evidence without manually opening multiple doctor files.

Implemented:

- `ReleaseEvidencePacket` now includes:
  - `product_readiness_status`;
  - `product_readiness_checks`;
  - `real_success_evidence`;
  - `real_failure_evidence`.
- `ari evidence packet` now writes `.ariadne/doctor/product_readiness.json` as
  part of packet generation and embeds the readiness summary into
  `.ariadne/evidence/release_evidence_packet.json`.
- Release evidence refs now include `product_readiness`.

Safety boundaries:

- Packet generation performs no external writes.
- Real success/failure evidence is read from local `.ariadne/` JSON artifacts.
- Failure evidence remains redacted and summarized by product doctor before it
  is embedded in release evidence.

Verification so far:

- `python3.11 -m pytest tests/test_release_evidence.py tests/test_v1_doctor_release.py -q`:
  passed, `10 passed`.
- `python3.11 -m pytest`: passed, `209 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ruff check ariadne_ltb/evidence.py ariadne_ltb/models.py tests/test_release_evidence.py`:
  passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local `.env` is
  reported as a redacted secret-scan finding.
- `python3.11 -m ariadne_ltb.cli evidence packet --output json`: passed and
  includes product readiness status plus real Codex, Claude Code, Feishu, and
  GitHub evidence summaries.
- `scripts/verify_v1.sh`: passed; release evidence packet generated as
  `release_evidence_2b62f61367c9`.

## 2026-06-18 00:35 CST Workbench Verification Integration Slice

Branch: `codex/ariadne-production-frontend-integration`

Branch integration decision:

- Rechecked `codex/ariadne-workbench-frontend-lane`; direct branch merge remains
  unsafe because it would roll back the current production backend line.
- Attempted to cherry-pick the latest frontend-only commit
  `21b1ff9084ad40d4567bfd726a3f2e5ff244c103`; the cherry-pick was empty,
  proving the frontend source changes are already present on the production
  integration branch.

Why this slice exists:

- The workbench frontend was present and manually buildable, but the release
  verification path did not exercise it.
- A production Agent Workbench should verify that the UI can consume the current
  local `.ariadne/` evidence snapshot, even though the frontend remains
  read-only and static.

Implemented:

- Added `scripts/verify_workbench.sh`.
- The script:
  - requires local `npm`;
  - installs frontend dependencies with `npm ci --prefer-offline` only when
    `node_modules` is missing;
  - runs `npm run sync:data`;
  - runs `npm run build`.
- Added `scripts/verify_workbench.sh` to `scripts/verify_v1.sh`.
- Updated root README and frontend README with the verification command.

Safety boundaries:

- The frontend remains read-only.
- `npm run sync:data` writes only ignored generated data under
  `frontend/ariadne-workbench/public/web_data/`.
- Generated frontend build output, node modules, and TypeScript build info stay
  ignored.

Verification so far:

- `cd frontend/ariadne-workbench && npm run sync:data`: passed and synced `8`
  tickets, `5` runtimes, and `18` inbox items.
- `cd frontend/ariadne-workbench && npm run build`: passed.
- `scripts/verify_workbench.sh`: passed.
- `scripts/verify_v1.sh`: passed; it now includes workbench data sync and
  production build. Release evidence packet generated as
  `release_evidence_232f98638ae9`.

## 2026-06-18 00:50 CST Product Acceptance Status Slice

Branch: `codex/ariadne-production-frontend-integration`

Why this slice exists:

- `ari doctor product` correctly reported unset write/execution gates as
  `action_required`, but that made the top-level readiness status ambiguous.
- For the production roadmap, there are two different questions:
  - whether Ariadne has enough real evidence to satisfy product acceptance;
  - whether the current shell environment is explicitly armed for a real write
    or execution right now.

Implemented:

- Added `production_acceptance_status` to `ari doctor product`.
- Added `run_gate_status` to `ari doctor product`.
- Kept `overall_status` / `Product readiness` as the immediate run-readiness
  status, so unset safety gates still surface as `action_required`.
- Added the same fields to `ReleaseEvidencePacket` and embedded them in
  `.ariadne/evidence/release_evidence_packet.json`.
- Updated README to explain the distinction between acceptance readiness and
  run gates.

Current local interpretation:

- `Production acceptance: ready`
- `Run gates: action_required`
- This means real DeepSeek, Codex, Claude Code, Feishu, GitHub, board,
  evidence, and workbench verification are present, while real writes/external
  execution still require explicit env gates at command time.

Verification so far:

- `python3.11 -m pytest tests/test_v1_doctor_release.py tests/test_release_evidence.py -q`:
  passed, `11 passed`.
- `python3.11 -m ruff check ariadne_ltb/doctor.py ariadne_ltb/evidence.py ariadne_ltb/models.py tests/test_v1_doctor_release.py tests/test_release_evidence.py`:
  passed.
- `python3.11 -m ariadne_ltb.cli doctor product`: passed and reports
  `Production acceptance: ready`, `Run gates: action_required`.
- `python3.11 -m ariadne_ltb.cli evidence packet --output json`: passed and
  includes `production_acceptance_status` and `run_gate_status`.
- `python3.11 -m pytest`: passed, `210 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; it still reports the
  local ignored `.env` finding with redacted secret values.
- `scripts/verify_v1.sh`: passed. The run generated release evidence packet
  `release_evidence_bdec3fe87c03` and verified the workbench data sync/build.

## 2026-06-18 01:12 CST Production Backend Default Slice

Branch: `codex/ariadne-production-frontend-integration`

Why this slice exists:

- The production roadmap says `fake-codex` is only for deterministic tests and
  offline fallback.
- Before this slice, several product paths still defaulted to `fake-codex`, so a
  user could run a normal ticket path and get a simulated success without
  explicitly choosing the offline backend.

Implemented:

- Added `ariadne_ltb/defaults.py` with separate defaults:
  - `PRODUCT_DEFAULT_BACKEND = "codex"`
  - `OFFLINE_TEST_BACKEND = "fake-codex"`
- Changed `ari ticket run` default backend to `codex`.
- Changed `TicketRunOrchestrator.run_ticket()` default backend to `codex`.
- Changed daemon fallback backend to `codex` when an assignment does not specify
  a backend.
- Changed the default Build Team implementer/backend to `codex`.
- Kept `demo full` and deterministic tests explicitly on `fake-codex` so offline
  verification remains stable.
- Updated README so the production quickstart uses Codex and the fake backend is
  documented as an offline regression path.

Behavioral impact:

- Running `ari ticket run ARI-003` without a backend now selects Codex.
- If `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1` and `--confirm-execution` are not
  both present, the Codex backend records blocked execution evidence instead of
  silently falling back to `fake-codex`.
- Offline tests and `ari demo full` still use `fake-codex` explicitly.

Verification so far:

- `python3.11 -m pytest tests/test_agent_teammate_mode.py tests/test_true_mvp_product_loop.py tests/test_multica_alignment.py tests/test_backlog_update_loop.py -q`:
  passed, `48 passed`.
- `python3.11 -m ariadne_ltb.cli ticket run ARI-003` against a temporary
  workspace: passed and selected `backend used: codex`; because the external
  execution gate was unset, it recorded a blocked Codex execution instead of
  falling back to `fake-codex`.
- `python3.11 -m pytest`: passed, `211 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed; this remains an explicit
  offline regression demo with `backend used: fake-codex`.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local ignored `.env`
  is still reported with redacted secret values.
- `scripts/verify_v1.sh`: passed. The run generated release evidence packet
  `release_evidence_6497590a3c9a` and verified workbench data sync/build.

## 2026-06-18 01:46 CST GitHub Product Evidence Coverage Slice

Branch: `codex/ariadne-production-frontend-integration`

Why this slice exists:

- The production roadmap requires real GitHub issue, PR, branch, status, and
  comment integration.
- Before this slice, `ari doctor product` treated any successful GitHub write
  result as enough GitHub product evidence. A successful issue comment sync could
  make GitHub look production-ready even if PR creation or status capture had
  never produced evidence.

Implemented:

- Upgraded product doctor GitHub evidence from a single latest-success check to
  operation-level coverage.
- `real_github_write_evidence` is now an aggregate check that is ready only when
  all required GitHub operations have successful evidence:
  - `create_issue`
  - `create_pr`
  - `sync`
  - `status`
- Added visible product checks:
  - `real_github_issue_evidence`
  - `real_github_pr_evidence`
  - `real_github_comment_evidence`
  - `real_github_status_evidence`
- Release evidence now embeds the aggregate GitHub operation coverage through
  `real_success_evidence.github.operations`.
- Updated README to explain that GitHub product acceptance requires issue, PR,
  comment sync, and status snapshot evidence.

Behavioral impact:

- A single successful `ari github sync` no longer satisfies production
  acceptance for GitHub.
- Full GitHub product acceptance requires persisted successful results from
  issue creation, PR creation, comment sync, and status read.
- No new remote writes are performed by the doctor; it only evaluates persisted
  local evidence.

Verification so far:

- `python3.11 -m pytest tests/test_v1_doctor_release.py tests/test_release_evidence.py tests/test_github_integration.py -q`:
  passed, `24 passed`.
- `python3.11 -m ariadne_ltb.cli doctor product`: passed and now reports
  `real_github_issue_evidence`, `real_github_pr_evidence`,
  `real_github_comment_evidence`, and `real_github_status_evidence` separately.
- `python3.11 -m ariadne_ltb.cli evidence packet --output json`: passed and
  includes `real_success_evidence.github.operations`.
- `python3.11 -m pytest`: passed, `212 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed; this remains explicit
  offline regression with `fake-codex`.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local ignored `.env`
  is still reported with redacted secret values.
- `scripts/verify_v1.sh`: passed. The run generated release evidence packet
  `release_evidence_95ae65cdd2bf` and verified workbench data sync/build.

## 2026-06-18 02:18 CST LLM Backlog Planner Slice

Branch: `codex/ariadne-production-frontend-integration`

Why this slice exists:

- Ariadne's product difference is not only assigning tickets to agents; it is
  using knowledge, feedback, memory, and codebase state to change the ticket
  backlog before the next agent run.
- Before this slice, the feedback-to-backlog loop was deterministic only. The
  generic `JSONLLMAgent` existed, and LLM planner/reviewer paths existed, but no
  DeepSeek-backed agent participated in the feedback-to-ticket update loop.

Implemented:

- Added `ariadne_ltb/llm_backlog.py`.
- Added `LLMBacklogPayload` / `LLMBacklogSuggestion` validation for structured
  DeepSeek output.
- Added `generate_llm_backlog_artifact()` to produce `llm_next_tickets.json`
  with the same `next_tickets` schema consumed by the existing backlog update
  engine.
- Missing `DEEPSEEK_API_KEY` or provider/schema failures write
  `llm_next_tickets_blocked.json` with a redacted reason and retain the
  deterministic next-ticket artifact as fallback evidence.
- Added `ari ticket run --backlog-planner deterministic|llm`.
- `TicketRunOrchestrator.run_ticket(..., backlog_planner="llm")` now calls the
  LLM backlog planner after memory/review and before `record_feedback_backlog_updates()`.
- Orchestrator result manifests now include:
  - `backlog_planner_name`
  - `backlog_planner_artifact_id`
  - `backlog_next_tickets_path`
  - `artifacts.backlog_planner_artifact_path`
- README now documents the LLM backlog planner path.

Behavioral impact:

- Default tests and offline loops remain deterministic.
- Production runs can now put a real DeepSeek-backed Memory/Build Lead style
  agent into the feedback-to-ticket update loop through `--backlog-planner llm`.
- When LLM backlog planning is blocked, Ariadne records the blocked LLM artifact
  instead of silently pretending the LLM path succeeded.

Verification so far:

- `python3.11 -m pytest tests/test_llm_backlog.py tests/test_backlog_update_loop.py tests/test_true_mvp_product_loop.py tests/test_llm_agents.py tests/test_llm_runtime.py -q`:
  passed, `40 passed`.
- `python3.11 -m ariadne_ltb.cli ticket run ARI-003 --backend fake-codex --backlog-planner llm`
  against a temporary workspace with `DEEPSEEK_API_KEY` unset: passed and wrote
  `llm_next_tickets_blocked.json` while continuing with deterministic backlog
  update evidence.
- `python3.11 -m pytest`: passed, `214 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed; this remains explicit
  offline regression with `fake-codex`.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local ignored `.env`
  is still reported with redacted secret values.
- `python3.11 -m ariadne_ltb.cli llm smoke --provider deepseek --confirm-external`:
  passed against the real DeepSeek API with `deepseek-v4-pro`; output reported
  structured JSON keys and `usage total tokens: 142`.
- `scripts/verify_v1.sh`: passed. The run generated release evidence packet
  `release_evidence_616123fc8eda` and verified workbench data sync/build.

## 2026-06-18 02:58 CST LLM Agent Evidence Gate Slice

Branch: `codex/ariadne-production-frontend-integration`

Why this slice exists:

- Ariadne already had DeepSeek runtime, LLM planner/reviewer, and the new LLM
  backlog planner path.
- Product acceptance still treated LLM readiness mostly as configuration:
  `DEEPSEEK_API_KEY` set. That is too weak for a production Agent Workbench.
- The product doctor and release packet should prove that real LLM agents have
  participated in the ticket loop, not merely that a key is available.

Implemented:

- Added `AriadneStore.list_build_packets()` for evidence aggregation.
- Added `real_llm_agent_evidence` to `ari doctor product`.
- LLM agent evidence is ready only when Ariadne has successful local records for:
  - LLM planner BuildPacket creation;
  - LLM reviewer execution;
  - LLM backlog planner `next_tickets` artifact generation.
- Added LLM agent success/failure summaries to
  `.ariadne/doctor/product_readiness.json`.
- Added `llm_agents` to release packet `real_success_evidence` and
  `real_failure_evidence`.
- Planner BuildPacket artifacts now persist `planner_mode`, so a later
  deterministic planning run can overwrite the current packet without erasing
  historical LLM planner evidence.
- Updated README so release evidence describes LLM agent evidence alongside
  Codex, Claude Code, Feishu, and GitHub evidence.

Real DeepSeek dogfood:

- `python3.11 -m ariadne_ltb.cli ticket plan ARI-003 --planner llm`: passed and
  wrote BuildPacket `packet_f9a69184a238`.
- `python3.11 -m ariadne_ltb.cli ticket run ARI-003 --backend fake-codex --planner llm --backlog-planner llm`:
  passed for the orchestrator path and wrote
  `.ariadne/artifacts/ticket_88fbff51677a/llm_next_tickets.json`.
- `python3.11 -m ariadne_ltb.cli review run ARI-003 --reviewer llm`: passed;
  reviewer mode was `llm`. The review verdict was `blocked` because it reviewed
  a blocked execution result; this is valid reviewer evidence, not an LLM
  runtime failure.
- `python3.11 -m ariadne_ltb.cli doctor product`: passed and reports
  `real_llm_agent_evidence: ready`, `Production acceptance: ready`, and
  `Run gates: action_required`.
- `python3.11 -m ariadne_ltb.cli evidence packet`: passed and generated
  `release_evidence_2523f5dde803`, whose `real_success_evidence.llm_agents`
  records planner/reviewer/backlog operation coverage.
- After preserving planner mode in BuildPacket artifact metadata, rerunning
  `python3.11 -m ariadne_ltb.cli ticket plan ARI-003 --planner llm` plus
  `python3.11 -m ariadne_ltb.cli doctor product` kept
  `real_llm_agent_evidence: ready` even after the default demo path rewrote the
  current BuildPacket.

Verification so far:

- `python3.11 -m pytest tests/test_v1_doctor_release.py tests/test_release_evidence.py -q`:
  passed, `12 passed`.
- `python3.11 -m ruff check ariadne_ltb/doctor.py ariadne_ltb/planner.py ariadne_ltb/storage.py tests/test_v1_doctor_release.py tests/test_release_evidence.py`:
  passed.
- `python3.11 -m pytest`: passed, `214 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local ignored `.env`
  remained redacted.
- `python3.11 -m ariadne_ltb.cli doctor product`: passed after demo rewrote the
  current packet and still reported `real_llm_agent_evidence: ready`.
- `scripts/verify_v1.sh`: passed. The run generated release evidence packet
  `release_evidence_e62746eb3b4c` and verified product doctor plus workbench
  sync/build.

## 2026-06-18 03:26 CST Ingest LLM Planner Visibility Slice

Branch: `codex/ariadne-production-frontend-integration`

Why this slice exists:

- The product acceptance command `ari ingest examples/sources/*.md --planner llm`
  works, but real LLM planning can take long enough that the CLI previously
  appeared silent.
- For a production Agent Workbench, long-running real agent steps need visible
  progress and exact blocked evidence.

Implemented:

- `ari ingest ... --planner <name>` now prints per-ticket planning progress:
  - `planning ARI-001 with llm...`
  - success lines with Build Packet id and handoff artifact path;
  - blocked lines with the exact error and planner error artifact path.
- Existing ingest behavior is preserved: source ingestion succeeds even if an
  optional planner is blocked, and the blocked planner writes evidence.

Real product check:

- `python3.11 -m ariadne_ltb.cli ingest examples/sources/*.md --planner llm`
  completed with real DeepSeek planning for four sources.

Verification so far:

- `python3.11 -m pytest tests/test_cli.py tests/test_1_0_full_demo.py tests/test_llm_runtime.py -q`:
  passed, `16 passed`.
- `python3.11 -m ruff check ariadne_ltb/cli.py tests/test_cli.py`: passed.

Final verification:

- `python3.11 -m pytest`: passed, `216 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed; the deterministic
  offline path still writes execution, review, memory, Feishu dry-run, next
  tickets, and board artifacts.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local ignored `.env`
  presence was reported without printing secret values.
- `scripts/verify_v1.sh`: passed. The run generated release evidence packet
  `release_evidence_e49a873baeab` and completed product doctor, release
  packet, workbench sync, and workbench build checks.

## 2026-06-18 02:14 CST Offline Demo Agent Artifact Wording Cleanup

Branch: `codex/ariadne-production-frontend-integration`

Why this slice exists:

- The legacy `ari demo` pipeline is still useful as a deterministic offline
  regression path, but its Build Lead and Planner artifacts still described
  Ariadne as if execution were permanently dry-run only.
- That wording conflicts with the production Agent Workbench roadmap where
  CodexBackend, ClaudeCodeBackend, DeepSeek, Feishu, and GitHub are real gated
  product capabilities.

Implemented:

- Updated `BuildLeadAgent` routing text so it states that Codex and Claude Code
  are production backends, while dry-run and fake-codex are offline test paths.
- Updated Planner-generated Build Packet, execution plan, and handoff wording
  so dry-run is framed as the offline regression path, not the product
  destination.
- Updated Feishu Plan run summary and next actions to point to the gated real
  Feishu write command instead of saying Feishu must remain dry-run.
- Added a regression test that fails if the legacy demo artifacts reintroduce
  `Execution backend remains dry-run only`, `No external APIs`, or
  `Feishu write plan is dry-run only`.

Verification:

- `python3.11 -m pytest tests/test_pipeline.py -q`: passed, `4 passed`.
- `python3.11 -m ruff check ariadne_ltb/agents.py tests/test_pipeline.py`:
  passed.
- `python3.11 -m pytest`: passed, `216 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local ignored `.env`
  remained redacted.
- `scripts/verify_v1.sh`: passed. The run generated release evidence packet
  `release_evidence_8ce89f2745e9` and completed product doctor, release
  packet, workbench sync, and workbench build checks.

## 2026-06-18 02:23 CST DeepSeek Role Agent Evidence Slice

Branch: `codex/ariadne-production-frontend-integration`

Why this slice exists:

- The production roadmap requires real DeepSeek upstream LLM runtime for Build
  Lead, planner, reviewer, memory, and knowledge agents.
- Before this slice, planner, reviewer, and LLM backlog evidence existed, but
  Build Lead / Knowledge / Memory roles only had a low-level helper and no
  persisted product command path.

Implemented:

- Added `ArtifactType.LLM_AGENT_RESULT`.
- Added `run_ticket_llm_agent(...)`, which:
  - starts and persists an `AgentRun`;
  - calls DeepSeek through the existing JSON LLM agent wrapper;
  - validates role output against a structured role payload;
  - writes `.ariadne/artifacts/<ticket_id>/llm_<role>.json`;
  - appends run messages, ticket events, and artifact refs.
- Added CLI command:
  - `ari llm run-agent <role> --ticket <ticket> --confirm-external`
  - fallback: `python3.11 -m ariadne_ltb.cli llm run-agent ...`
- The command requires `--confirm-external` before any real DeepSeek request.
- Extended product doctor / release evidence so `real_llm_agent_evidence` now
  requires:
  - `build_lead`;
  - `knowledge`;
  - `memory`;
  - `planner`;
  - `reviewer`;
  - `backlog`.

Bug found and fixed during real dogfood:

- A real `build_lead` run initially failed before calling DeepSeek because
  `_role_prompt` assumed `MemoryRecord.ticket_key` and `MemoryRecord.review_verdict`
  existed.
- Root cause: the actual `MemoryRecord` model uses `ticket_id`, `title`,
  `review_summary`, and `build_summary`.
- Added a regression fixture with an existing `MemoryRecord` and fixed prompt
  construction to use the real model fields.
- A concurrent real Knowledge / Memory dogfood run also exposed a lost-update
  risk when two LLM role runs update the same ticket. `_finish_llm_run` now
  reloads the ticket and reasserts `with_run(finished.id)` before writing
  artifacts/events.
- `run_ticket_llm_agent(...)` now catches prompt/call failures before
  completion, writes a blocked `llm_agent_result` artifact, terminates the
  `AgentRun`, and redacts the active client API key from error text.

Real DeepSeek dogfood:

- `python3.11 -m ariadne_ltb.cli llm run-agent build_lead --ticket ARI-003 --confirm-external`:
  passed, model `deepseek-v4-pro`, total tokens `2405`, artifact
  `.ariadne/artifacts/ticket_88fbff51677a/llm_build_lead.json`.
- `python3.11 -m ariadne_ltb.cli llm run-agent knowledge --ticket ARI-003 --confirm-external`:
  passed, model `deepseek-v4-pro`, total tokens `2428`, artifact
  `.ariadne/artifacts/ticket_88fbff51677a/llm_knowledge.json`.
- `python3.11 -m ariadne_ltb.cli llm run-agent memory --ticket ARI-003 --confirm-external`:
  passed, model `deepseek-v4-pro`, total tokens `2292`, artifact
  `.ariadne/artifacts/ticket_88fbff51677a/llm_memory.json`.
- `python3.11 -m ariadne_ltb.cli doctor product`: passed and reports
  `real_llm_agent_evidence: ready` with operations
  `backlog/build_lead/knowledge/memory/planner/reviewer`.
- `python3.11 -m ariadne_ltb.cli doctor store`: passed after relinking one
  valid Knowledge run produced during the lost-update bug investigation.
- `python3.11 -m ariadne_ltb.cli evidence packet`: passed and reports store
  invariants `ok`.

Verification:

- `python3.11 -m pytest tests/test_llm_agents.py tests/test_v1_doctor_release.py tests/test_release_evidence.py -q`:
  passed, `18 passed`.
- `python3.11 -m ruff check ariadne_ltb/llm_agents.py ariadne_ltb/doctor.py ariadne_ltb/cli.py ariadne_ltb/models.py tests/test_llm_agents.py tests/test_v1_doctor_release.py`:
  passed.
- `python3.11 -m pytest`: passed, `220 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed; reviewer verdict `pass`.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local ignored `.env`
  remained redacted.
- `scripts/verify_v1.sh`: passed. The run generated release evidence packet
  `release_evidence_f1b60a42045b` and completed product doctor, release
  packet, workbench sync, and workbench build checks.

## 2026-06-18 02:31 CST Ticket Run LLM Agent Runtime Slice

Branch: `codex/ariadne-production-frontend-integration`

Why this slice exists:

- DeepSeek role agents were available through `ari llm run-agent`, but the
  normal product loop `ari ticket run ...` still did not invoke Build Lead,
  Knowledge, or Memory upstream LLM roles.
- The production target says the common ticket loop should flow through real
  LLM agents when configured, not require a user to manually stitch separate
  role commands around `ticket run`.

Implemented:

- Added `agent_runtime` to `TicketRunOrchestrator.run_ticket(...)`:
  - `deterministic` remains the default;
  - `llm` invokes DeepSeek Build Lead before planning, Knowledge after Build
    Packet/handoff creation, and Memory after review/memory/backlog update.
- Added `--agent-runtime deterministic|llm` to `ari ticket run`.
- Added `agent_runtime` and `llm_agent_artifact_paths` to `TicketRunResult` and
  orchestrator result manifests.
- `ari ticket run ... --agent-runtime llm` now prints the LLM role artifact
  paths in CLI output.
- README now documents both `ari llm run-agent ...` and the integrated
  `ari ticket run ... --agent-runtime llm` product path.

Real DeepSeek dogfood:

- `python3.11 -m ariadne_ltb.cli ticket run ARI-003 --backend fake-codex --agent-runtime llm`:
  passed.
- The run invoked real DeepSeek role agents and wrote:
  - `.ariadne/artifacts/ticket_88fbff51677a/llm_build_lead.json`
  - `.ariadne/artifacts/ticket_88fbff51677a/llm_knowledge.json`
  - `.ariadne/artifacts/ticket_88fbff51677a/llm_memory.json`
- The full loop continued through fake-codex offline execution, review,
  memory, Feishu dry-run plan, next tickets, backlog updates, and board export.
- Reviewer verdict: `pass`.

Verification:

- `python3.11 -m pytest tests/test_true_mvp_product_loop.py -q`: passed,
  `16 passed`.
- `python3.11 -m ruff check ariadne_ltb/orchestrator.py ariadne_ltb/cli.py tests/test_true_mvp_product_loop.py`:
  passed.
- `python3.11 -m pytest`: passed, `221 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed; reviewer verdict `pass`.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local ignored `.env`
  remained redacted.
- `python3.11 -m ariadne_ltb.cli doctor product`: passed and kept
  `real_llm_agent_evidence: ready`.
- `scripts/verify_v1.sh`: passed. The run generated release evidence packet
  `release_evidence_db080fc377cc` and completed product doctor, release
  packet, workbench sync, and workbench build checks.

## 2026-06-18 02:41 CST Daemon LLM Runtime Strategy Slice

Branch: `codex/ariadne-production-frontend-integration`

Why this slice exists:

- `ari ticket run ... --agent-runtime llm` could invoke DeepSeek Build Lead,
  Knowledge, and Memory roles, but the roadmap's normal product path is
  assignment-centered: `ari ticket assign ...` followed by `ari daemon run-once`.
- Before this slice, daemon workers always called the orchestrator with the
  assignment planner and deterministic upstream agent runtime defaults. That
  meant the daemon path could still bypass real upstream LLM agents even when
  the ticket-run path supported them.

Implemented:

- Added runtime strategy fields to the local work-management model:
  - `AgentProfile.agent_runtime`
  - `AgentProfile.backlog_planner_name`
  - `BuildTeam.agent_runtime`
  - `BuildTeam.backlog_planner_name`
  - `TicketAssignment.agent_runtime`
  - `TicketAssignment.backlog_planner_name`
  - `RouteDecision.agent_runtime`
  - `RouteDecision.backlog_planner_name`
- Added strategy overrides to `ari ticket assign`:
  - `--planner`
  - `--agent-runtime deterministic|llm`
  - `--backlog-planner deterministic|llm`
- `LocalDaemonWorker.run_once(...)` now passes assignment strategy into
  `TicketRunOrchestrator.run_ticket(...)`.
- Explicit `agent_runtime=llm` now treats a blocked DeepSeek role as a blocked
  ticket run instead of allowing execution to continue and marking the
  assignment done.
- `ari daemon run-once` and `ari daemon start` can override assignment strategy
  for one worker pass with `--agent-runtime` and `--backlog-planner`.
- The board Route Decision section now shows Agent Runtime and Backlog Planner.
- README now documents the assignment-centered LLM runtime path:

```bash
ari ticket assign ARI-003 --to codex --agent-runtime llm --backlog-planner llm
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari daemon run-once --confirm-execution
```

Deterministic tests:

- Added coverage that `ari ticket assign` persists planner/runtime/backlog
  planner overrides on assignments.
- Added daemon coverage using a fake DeepSeek transport to prove
  `LocalDaemonWorker.run_once(agent_runtime="llm")` invokes Build Lead,
  Knowledge, and Memory LLM role AgentRuns inside the assignment-centered path.
- Added daemon coverage proving that missing `DEEPSEEK_API_KEY` fails the
  assignment instead of reporting a successful run.
- Added board coverage for Route Decision Agent Runtime and Backlog Planner.

Verification:

- Targeted deterministic tests:
  `python3.11 -m pytest tests/test_agent_teammate_mode.py tests/test_v1_daemon_supervision.py tests/test_true_mvp_product_loop.py -q`
  passed, `36 passed`.
- Targeted Ruff:
  `python3.11 -m ruff check ariadne_ltb/models.py ariadne_ltb/storage.py ariadne_ltb/team.py ariadne_ltb/daemon.py ariadne_ltb/cli.py ariadne_ltb/board.py tests/test_agent_teammate_mode.py`
  passed.
- Real DeepSeek daemon dogfood:
  `ari ticket assign ARI-003 --to fake-codex --agent-runtime llm` followed by
  `ari daemon run-once --agent-runtime llm` passed on a temporary Ariadne root
  with the local ignored `.env` loaded.
- The daemon-centered dogfood wrote successful role artifacts:
  - `llm_build_lead.json`: model `deepseek-v4-pro`, total tokens `2748`;
  - `llm_knowledge.json`: model `deepseek-v4-pro`, total tokens `2564`;
  - `llm_memory.json`: model `deepseek-v4-pro`, total tokens `2423`.
- Reviewer verdict: `pass`; assignment status: `done`.
- A temporary-root run without `.env` now exits the daemon pass with
  `assignment failed` because `DEEPSEEK_API_KEY` is missing. This prevents an
  explicit LLM-runtime request from being misreported as a completed assignment.
- Full `python3.11 -m pytest`: passed, `224 passed`.
- Full `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed; reviewer verdict `pass`.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local ignored `.env`
  remained redacted.
- `scripts/verify_v1.sh`: passed. The run generated release evidence packet
  `release_evidence_209859c72b9a` and completed product doctor, release
  packet, workbench sync, and workbench build checks.

## 2026-06-18 02:57 CST Real Backend Smoke Through Daemon Slice

Branch: `codex/ariadne-production-frontend-integration`

Why this slice exists:

- `ari backend smoke-test codex` existed, but it was Codex-only and directly
  invoked `TicketRunOrchestrator`.
- The production roadmap's main loop is assignment-centered:
  `ticket -> assignment -> daemon/runtime -> backend -> review/memory/board`.
  A real backend smoke test should prove that route, not only a direct
  orchestrator call.

Implemented:

- `ari backend smoke-test` now accepts both `codex` and `claude-code`.
- The smoke command now uses:

```text
source fixtures -> selected code_task ticket -> assignment -> LocalDaemonWorker
  -> TicketRunOrchestrator -> backend execution -> review -> memory -> board
```

- The command still refuses before creating demo target state unless both real
  execution gates are present:
  - `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1`
  - `--confirm-execution`
- The command prints assignment id/status, handoff file, execution result, exit
  code, changed files, test exit code, review verdict, agent runtime, backlog
  planner, board, memory, Feishu dry-run plan, and next tickets.
- If the assignment does not finish as `done`, the smoke command exits non-zero
  after printing the blocker/evidence.
- `ari daemon run-once/start` now accept `--timeout-seconds`, so smoke-test
  timeout policy reaches the real backend command through the daemon path.
- README now documents Codex and Claude Code smoke tests as real backend smoke
  tests through assignment + daemon.
- `docs/real_codex_smoke_test.md` now states that `backend smoke-test codex`
  reaches the orchestrator through `LocalDaemonWorker`.

Deterministic tests:

- Added a deterministic codex smoke-test fixture using a local Python command
  template. It modifies only the demo target allowed files and proves the smoke
  command reaches `assignment status: done` through daemon execution.
- Added a claude-code missing-command gate test.
- Existing missing external flag and missing confirmation tests still assert
  the command refuses before creating demo target state.

Real smoke evidence:

- Real Codex smoke through daemon:
  - command:
    `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 python3.11 -m ariadne_ltb.cli --root <tmp> backend smoke-test codex --confirm-execution --timeout-seconds 240`
  - result: passed;
  - assignment: `assignment_94b12b37f988`, status `done`;
  - execution: `execution_94b12b37f988`, exit code `0`;
  - changed files: `demo_todo/cli.py`, `tests/test_cli.py`;
  - test exit code: `0`;
  - review verdict: `pass`.
- Real Claude Code smoke through daemon:
  - command:
    `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 python3.11 -m ariadne_ltb.cli --root <tmp> backend smoke-test claude-code --confirm-execution --timeout-seconds 240`
  - result: passed;
  - assignment: `assignment_3dbb88f5eb03`, status `done`;
  - execution: `execution_3dbb88f5eb03`, exit code `0`;
  - changed files: `demo_todo/cli.py`, `tests/test_cli.py`;
  - test exit code: `0`;
  - review verdict: `pass`.
- Real DeepSeek + Codex combined daemon smoke:
  - command:
    `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 python3.11 -m ariadne_ltb.cli --root <tmp> backend smoke-test codex --confirm-execution --timeout-seconds 240 --agent-runtime llm`
  - result: passed;
  - assignment: `assignment_88d774e0b547`, status `done`;
  - execution: `execution_870ac3fd1895`, exit code `0`;
  - changed files: `demo_todo/cli.py`, `tests/test_cli.py`;
  - test exit code: `0`;
  - review verdict: `pass`;
  - `llm_build_lead.json`: model `deepseek-v4-pro`, total tokens `2210`;
  - `llm_knowledge.json`: model `deepseek-v4-pro`, total tokens `2259`;
  - `llm_memory.json`: model `deepseek-v4-pro`, total tokens `2526`.

Verification:

- `python3.11 -m pytest tests/test_backend_smoke_cli.py -q`: passed,
  `11 passed`.
- `python3.11 -m ruff check ariadne_ltb/cli.py ariadne_ltb/daemon.py tests/test_backend_smoke_cli.py`:
  passed.
- Full `python3.11 -m pytest`: passed, `226 passed`.
- Full `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed; reviewer verdict `pass`.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local ignored `.env`
  remained redacted.
- `scripts/verify_v1.sh`: passed. The run generated release evidence packet
  `release_evidence_db825ed5373f` and completed product doctor, release
  packet, workbench sync, and workbench build checks.

## 2026-06-18 10:18 CST Backend Smoke Evidence Persistence Slice

Branch: `codex/ariadne-production-frontend-integration`

Why this slice exists:

- Real Codex and Claude Code smoke tests already ran through assignment +
  daemon, but their success evidence was mostly terminal output and narrative
  report text.
- Product doctor and release evidence need a first-class, structured artifact
  proving that a real backend smoke run completed the full loop.

Implemented:

- Added `BackendSmokeEvidence` as a persistent model for real backend smoke
  results.
- Added `.ariadne/evidence/backend_smoke/<backend>/<evidence_id>.json` storage
  plus store list/save APIs.
- Updated `ari backend smoke-test codex|claude-code` so daemon smoke runs save
  structured evidence on both success and daemon-result failure paths.
- Updated product doctor so `real_codex_execution_evidence` and
  `real_claude_execution_evidence` prefer backend smoke evidence, while keeping
  legacy `ExecutionResult` inference as compatibility fallback.
- Added `backend_smoke_evidence` to release evidence packet refs.
- Updated README and `docs/real_codex_smoke_test.md` with the new evidence path.

Deterministic verification so far:

- `python3.11 -m pytest tests/test_backend_smoke_cli.py tests/test_release_evidence.py tests/test_v1_doctor_release.py`:
  passed, `23 passed`.
- `python3.11 -m ruff check ariadne_ltb/models.py ariadne_ltb/storage.py ariadne_ltb/cli.py ariadne_ltb/doctor.py ariadne_ltb/evidence.py tests/test_backend_smoke_cli.py tests/test_release_evidence.py tests/test_v1_doctor_release.py`:
  passed.

Verification:

- Full `python3.11 -m pytest`: passed, `226 passed`.
- Full `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed; reviewer verdict `pass`.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local ignored `.env`
  remained redacted.
- `scripts/verify_v1.sh`: passed. The run generated release evidence packet
  `release_evidence_45590e559449` and completed product doctor, release
  packet, workbench sync, and workbench build checks.

Fresh real smoke evidence:

- Real Codex smoke through daemon:
  - result: passed;
  - assignment: `assignment_5e959d764cb0`, status `done`;
  - execution: `execution_5e959d764cb0`, exit code `0`;
  - changed files: `demo_todo/cli.py`, `tests/test_cli.py`;
  - test exit code: `0`;
  - review verdict: `pass`;
  - smoke evidence:
    `/tmp/ariadne-smoke-codex-tQlfcr/.ariadne/evidence/backend_smoke/codex/backend_smoke_c7239143e89b.json`.
- Real Claude Code smoke through daemon:
  - result: passed;
  - assignment: `assignment_199dc7a10fc3`, status `done`;
  - execution: `execution_199dc7a10fc3`, exit code `0`;
  - changed files: `demo_todo/cli.py`, `tests/test_cli.py`;
  - test exit code: `0`;
  - review verdict: `pass`;
  - smoke evidence:
    `/tmp/ariadne-smoke-claude-15BVqf/.ariadne/evidence/backend_smoke/claude-code/backend_smoke_e081d82f82c4.json`.
- Product doctor confirmed the new artifacts are machine-readable:
  - Codex temp root: `real_codex_execution_evidence: ready`, source
    `backend_smoke`.
  - Claude temp root: `real_claude_execution_evidence: ready`, source
    `backend_smoke`.

## 2026-06-18 10:42 CST Workbench Backend Smoke Evidence Slice

Branch: `codex/ariadne-production-frontend-integration`

Branch integration decision:

- The separate `codex/ariadne-workbench-frontend-lane` branch was re-checked.
  It is based on an older core baseline; merging it directly would delete or
  overwrite current runtime, evidence, doctor, and roadmap work.
- Instead of merging the stale branch, this slice ports the useful frontend
  direction into the production integration branch by consuming the stable
  backend smoke evidence data contract.

Implemented:

- `frontend/ariadne-workbench/scripts/sync-local-data.mjs` now reads
  `.ariadne/evidence/backend_smoke/<backend>/*.json`.
- Workbench data now includes `backendSmokeEvidence` and each ticket can expose
  its latest `backendSmoke` record.
- The runtime page now shows a `Backend smoke evidence` table for recent Codex
  and Claude Code smoke runs.
- The issue inspector now includes a `Backend smoke` panel with assignment,
  execution id, exit code, test exit code, review verdict, changed files,
  handoff path, and board path.
- Backend smoke success records are also surfaced into the inbox integration
  stream.

Verification:

- Copied the latest ignored real Codex and Claude smoke evidence artifacts into
  the local ignored `.ariadne/evidence/backend_smoke/` directory for frontend
  sync verification.
- `npm --prefix frontend/ariadne-workbench run sync:data`: passed and synced
  `2` backend smoke evidence records.
- `npm --prefix frontend/ariadne-workbench run build`: passed.
- Browser QA through local Vite (`http://127.0.0.1:4178/`) confirmed the runtime
  page renders `Backend smoke evidence` with both `codex` and `claude-code`
  passed rows.
- Full `python3.11 -m pytest`: passed, `226 passed`.
- Full `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed; reviewer verdict `pass`.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local ignored `.env`
  remained redacted.
- `scripts/verify_v1.sh`: passed. The run generated release evidence packet
  `release_evidence_9fadcda12b24` and completed product doctor, release
  packet, workbench sync, and workbench build checks.

Known UI limitation:

- The issue board currently has no direct ticket-key search. Clicking text that
  contains `ARI-003` can select a related follow-up ticket such as `ARI-009`.
  The ticket inspector can display backend smoke evidence when the executed
  ticket is selected, but a future slice should add explicit ticket search or a
  stable detail route.

## 2026-06-18 03:20 CST Workbench Issue Deep Link And Search Slice

Branch: `codex/ariadne-production-frontend-integration`

Implemented:

- Added stable workbench hash routes for pages and issue details, including
  `#issues/<ticket_key>`.
- Added issue selection routing so clicking a ticket updates the URL to the
  selected ticket key.
- Added `hashchange` handling so pasted links such as `#issues/ARI-003` select
  the correct ticket after local workbench data loads.
- Added issue search across key, title, summary, owner, decision, review
  verdict, backend smoke backend, and GitHub branch.
- Made exact ticket-key searches such as `ARI-003` match only that ticket key
  or id, preventing related follow-up tickets like `ARI-009` from hijacking
  manual review.
- Added CSS for the search row and adjusted the issue board height/padding.

Verification:

- `npm --prefix frontend/ariadne-workbench run sync:data`: passed and synced
  local workbench data.
- `npm --prefix frontend/ariadne-workbench run build`: passed.
- Browser QA through local Vite (`http://127.0.0.1:4178/#issues/ARI-003`)
  confirmed:
  - the inspector selected `ARI-003`;
  - backend smoke evidence remained visible for that ticket;
  - searching `ARI-003` returned `1 / 9`;
  - the visible cards did not include `ARI-009`.
- Full `python3.11 -m pytest`: passed, `226 passed`.
- Full `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed; reviewer verdict
  `pass`.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local ignored
  `.env` remained redacted and no secret value was printed.
- `scripts/verify_v1.sh`: passed. The run generated release evidence packet
  `release_evidence_8c4471fea35c` and completed product doctor, release
  packet, workbench sync, and workbench build checks.

Result:

- The previous UI limitation around selecting `ARI-003` from text that also
  mentioned related tickets is resolved for direct issue-key review paths.

## 2026-06-18 03:25 CST Evidence Search Coverage Slice

Branch: `codex/ariadne-production-frontend-integration`

Problem found during production-goal audit:

- `ari evidence packet` already wrote production acceptance fields such as
  `real_codex_execution_evidence`.
- Backend smoke evidence for real Codex and Claude Code existed under
  `.ariadne/evidence/backend_smoke/`.
- `ari search "real_codex_execution_evidence"` returned no matches, so a user
  could not discover production acceptance evidence through the local evidence
  search surface.

Implemented:

- Added `backend_smoke` documents to local search indexing.
- Added the release evidence packet as a `release_evidence` document when
  `.ariadne/evidence/release_evidence_packet.json` exists.
- Extended deterministic local search tests to prove backend smoke and release
  evidence are searchable.

Verification:

- `python3.11 -m pytest tests/test_local_search.py -q`: passed, `2 passed`.
- `python3.11 -m ruff check ariadne_ltb/local_search.py tests/test_local_search.py`:
  passed.
- `python3.11 -m ariadne_ltb.cli search "real_codex_execution_evidence" --output json`:
  returned a `release_evidence` hit pointing at
  `.ariadne/evidence/release_evidence_packet.json`.
- `python3.11 -m ariadne_ltb.cli search "backend_smoke execution_5e959d764cb0" --output json`:
  returned both `release_evidence` and `backend_smoke` hits, including the real
  Codex backend smoke artifact for `ARI-003`.
- Full `python3.11 -m pytest`: passed, `226 passed`.
- Full `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed; reviewer verdict
  `pass`.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local ignored
  `.env` remained redacted and no secret value was printed.
- `scripts/verify_v1.sh`: passed. The run generated release evidence packet
  `release_evidence_897a0539e2f6` and completed product doctor, release
  packet, workbench sync, and workbench build checks.

Result:

- Production acceptance evidence is now discoverable through the same local
  search surface as tickets, comments, memory, artifacts, reviews, inbox,
  Feishu results, GitHub results, and execution results.

## 2026-06-18 03:29 CST Board Production Acceptance Evidence Slice

Branch: `codex/ariadne-production-frontend-integration`

Problem found during production-goal audit:

- `ari doctor product` already reported `Production acceptance: ready`.
- `ari evidence packet` already recorded real DeepSeek, Codex, Claude Code,
  Feishu, and GitHub evidence.
- The static board showed the release evidence packet path, but it did not
  surface the production acceptance status, readiness checks, or real success
  evidence near the top-level board summary.

Implemented:

- Added a `Production Acceptance Evidence` section to the exported markdown
  board.
- The section reads local `product_readiness.json` and
  `release_evidence_packet.json` only; it does not perform external checks or
  writes.
- The board now shows:
  - product readiness status;
  - production acceptance status;
  - run gate status;
  - product readiness checks with next actions;
  - real success evidence for LLM agents, Codex, Claude Code, Feishu, and
    GitHub;
  - latest failure evidence when present.
- Added deterministic board test coverage for production acceptance evidence.

Verification so far:

- `python3.11 -m pytest tests/test_v1_board_ux.py -q`: passed, `6 passed`.
- `python3.11 -m ruff check ariadne_ltb/board.py tests/test_v1_board_ux.py`:
  passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- Manual board inspection confirmed the generated board includes:
  - `Production acceptance: ready`;
  - `real_codex_execution_evidence: ready`;
  - real Codex backend smoke evidence;
  - real Claude Code backend smoke evidence;
  - real Feishu document URL;
  - real GitHub issue, PR, comment, and operation evidence.
- Full `python3.11 -m pytest`: passed, `227 passed`.
- Full `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed; reviewer verdict
  `pass`.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local ignored
  `.env` remained redacted and no secret value was printed.
- `scripts/verify_v1.sh`: passed. The run generated release evidence packet
  `release_evidence_c2e9b6a7219d` and completed product doctor, release
  packet, workbench sync, and workbench build checks.

Result:

- The static board is now a top-level review surface for production acceptance
  evidence, instead of requiring reviewers to inspect doctor JSON or release
  evidence JSON directly.

## 2026-06-18 03:34 CST Ticket Production Evidence Trace Slice

Branch: `codex/ariadne-production-frontend-integration`

Problem found during production-goal audit:

- The board, search, release packet, and product doctor could show production
  evidence, but `ari ticket show ARI-003` still only showed ticket counts,
  artifact counts, and latest assignment.
- A user starting from a single ticket could not directly trace that ticket to
  real Codex, Claude Code, DeepSeek LLM agent, Feishu, GitHub, or release
  evidence.

Implemented:

- Extended `ari ticket show <ticket>` with a `Production Evidence` section.
- The section shows:
  - backend smoke evidence per backend, including execution result, test exit
    code, review verdict, and evidence path;
  - latest DeepSeek LLM role artifacts, grouped by role;
  - latest Feishu write result and document URL;
  - GitHub operations plus issue, PR, and comment URL evidence;
  - release packet production acceptance and product readiness status.
- The command reads only local evidence files and does not trigger external
  execution or writes.
- Added deterministic test coverage for the enriched ticket show output.

Verification so far:

- `python3.11 -m pytest tests/test_v1_board_ux.py::test_cli_outputs_readable_ticket_state -q`:
  passed.
- `python3.11 -m ruff check ariadne_ltb/cli.py tests/test_v1_board_ux.py`:
  passed.
- `python3.11 -m ariadne_ltb.cli ticket show ARI-003` on the current local
  store now shows:
  - real Codex backend smoke evidence;
  - real Claude Code backend smoke evidence;
  - DeepSeek LLM role artifacts for build lead, knowledge, and memory;
  - real Feishu document URL;
  - real GitHub issue, PR, and comment URL;
  - release packet `production_acceptance=ready`.
- `python3.11 -m pytest`: passed, `227 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local `.env`
  secrets were reported only as redacted.
- `scripts/verify_v1.sh`: passed and generated release evidence packet
  `release_evidence_acdf7befb841`.

Result:

- A reviewer can now start from one Build Ticket and trace its real production
  integration evidence without manually searching the board or release packet.

## 2026-06-18 04:06 CST Workbench Production Evidence Contract Slice

Branch: `codex/ariadne-production-frontend-integration`

Branch integration decision:

- Re-checked `codex/ariadne-workbench-frontend-lane` against the current
  production branch.
- Full merge is deferred because the frontend lane was cut from an older base;
  merging it directly would delete current production backend modules, doctors,
  tests, roadmap files, and evidence surfaces.
- The current branch already contains the stable workbench shell, hash routing,
  issue search, local data sync, GitHub panel, backend smoke panel, and
  workbench verification.
- The safe integration move for this slice was to extend the current workbench
  data contract rather than merge the stale branch wholesale.

Implemented:

- Extended the workbench data model with ticket-level:
  - DeepSeek LLM role agent evidence;
  - Feishu write evidence;
  - release evidence packet summary.
- Updated `sync-local-data.mjs` to read:
  - `.ariadne/artifact_index/*.json` for `llm_agent_result` artifacts;
  - `.ariadne/integrations/feishu/<ticket_key>/*.json`;
  - `.ariadne/evidence/release_evidence_packet.json`.
- Added `ARIADNE_WORKBENCH_ARIADNE_ROOT` and
  `ARIADNE_WORKBENCH_OUTPUT_PATH` so the sync contract can be tested against a
  temporary Ariadne store without touching the real workspace snapshot.
- Updated the ticket inspector to show `LLM agents`, `Feishu`, and `Release
  packet` panels beside the existing GitHub and backend smoke evidence.
- Added deterministic test coverage for the generated workbench JSON evidence
  fields.

Verification so far:

- `python3.11 -m pytest tests/test_workbench_data_sync.py tests/test_v1_board_ux.py -q`:
  passed, `7 passed`.
- `python3.11 -m ruff check tests/test_workbench_data_sync.py`: passed.
- `npm run sync:data && npm run build` from `frontend/ariadne-workbench`:
  passed.
- `python3.11 -m pytest`: passed, `228 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local `.env`
  secret was reported only as `[REDACTED]`.
- `scripts/verify_v1.sh`: passed and generated release evidence packet
  `release_evidence_50de889966b1`; this also ran product doctor, integration
  doctor, store doctor, workbench sync, and workbench build.

Result:

- The web workbench can now start from one ticket and show the same production
  evidence chain as the CLI: real LLM agent output, Feishu write evidence,
  backend execution evidence, GitHub evidence, and release packet status.

## 2026-06-18 04:29 CST Production Acceptance Gate Slice

Branch: `codex/ariadne-production-frontend-integration`

Problem found during product-path audit:

- `doctor product` already separated production acceptance from current run
  gates, but it only reported statuses.
- `scripts/verify_v1.sh` still executed `fake-codex` as part of the release
  verification flow without an explicit production-acceptance assertion.
- Operator-facing release/demo docs still presented `fake-codex` as the normal
  release path, which conflicted with the production-first roadmap.

Implemented:

- Added `ari doctor product --require-acceptance-ready`.
  - The command exits non-zero unless real production acceptance evidence is
    `ready`.
  - It does not require current run gates to be open; external execution and
    Feishu writes remain default-off until explicitly confirmed.
- Added `ari doctor product --require-run-gates-ready` for cases where an
  operator intentionally wants to assert that execution/write gates are set for
  a live run.
- Updated `scripts/verify_v1.sh`:
  - uses `python3.11 -m pytest`;
  - uses `python3.11 -m ruff check .`;
  - labels `fake-codex` as a deterministic regression loop only;
  - enforces `doctor product --require-acceptance-ready`.
- Updated `README.md`, `docs/ops/V1_RELEASE_CHECKLIST.md`, and
  `docs/ops/HUMAN_DEMO_SCRIPT.md` so production flow points to real Codex,
  DeepSeek LLM agents, Feishu, GitHub, board, and release evidence. The
  `fake-codex` flow is now explicitly documented as deterministic fallback.
- Added deterministic tests for the new product doctor requirements and release
  script guard.

Verification so far:

- `python3.11 -m pytest tests/test_v1_doctor_release.py tests/test_v1_docs.py -q`:
  passed, `14 passed`.
- `python3.11 -m ruff check ariadne_ltb/cli.py ariadne_ltb/doctor.py tests/test_v1_doctor_release.py`:
  passed.
- `python3.11 -m ariadne_ltb.cli doctor product --require-acceptance-ready`:
  passed on the current local store, with production acceptance `ready` and run
  gates `action_required`.
- `python3.11 -m pytest`: passed, `228 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local `.env`
  secret was reported only as `[REDACTED]`.
- `scripts/verify_v1.sh`: passed with
  `doctor product --require-acceptance-ready`; the run generated release
  evidence packet `release_evidence_caa850075e2a`.

Result:

- The release verification path can no longer pass solely because the
  deterministic fake backend works. It now requires previously captured real
  production evidence for LLM agents, Codex, Claude Code, Feishu, and GitHub.

## 2026-06-18 03:55 CST Release Evidence Packet Gate Slice

Branch: `codex/ariadne-production-frontend-integration`

Problem found during release evidence audit:

- `ari doctor product --require-acceptance-ready` already enforced production
  acceptance, but `ari evidence packet` still succeeded as a pure reporting
  command.
- `scripts/verify_v1.sh` generated the release evidence packet without asking
  the packet command itself to fail when production acceptance was not ready.
- This left one release artifact path that could still look successful in a
  demo-only or fake-only store.

Implemented:

- Added `ari evidence packet --require-acceptance-ready`.
  - The command still writes `.ariadne/evidence/release_evidence_packet.json`.
  - It exits with code 2 unless `production_acceptance_status == ready`.
- Added `ari evidence packet --require-run-gates-ready`.
  - This is stricter and requires the current real execution/write run gates to
    be ready as well.
  - It remains optional because normal local safety keeps external execution and
    Feishu writes gated until explicitly confirmed.
- Expanded table output to show:
  - production acceptance;
  - product readiness;
  - run gates.
- Updated `scripts/verify_v1.sh` so release verification now runs
  `ari evidence packet --require-acceptance-ready`.
- Updated `README.md`, `docs/ops/V1_RELEASE_CHECKLIST.md`,
  `docs/ops/HUMAN_DEMO_SCRIPT.md`, the production roadmap, and the execution
  plan so future agents use the gated release packet command.
- Added deterministic tests proving:
  - fake-only stores fail `--require-acceptance-ready`;
  - production acceptance can be ready while run gates remain action-required;
  - `--require-run-gates-ready` fails in that default-safe state.

Verification:

- `python3.11 -m pytest tests/test_release_evidence.py tests/test_v1_doctor_release.py -q`:
  passed, `14 passed`.
- `python3.11 -m ruff check ariadne_ltb/cli.py tests/test_release_evidence.py`:
  passed.
- `python3.11 -m ariadne_ltb.cli evidence packet --help`: passed and shows both
  new requirement flags.
- `python3.11 -m ariadne_ltb.cli evidence packet --require-acceptance-ready`:
  passed on the current local store with production acceptance `ready`, product
  readiness `action_required`, and run gates `action_required`.
- `python3.11 -m ariadne_ltb.cli evidence packet --output json --require-acceptance-ready`:
  passed and returned `production_acceptance_status=ready`.
- `python3.11 -m pytest`: passed, `230 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local `.env` was
  reported only as `[REDACTED]`.
- `scripts/verify_v1.sh`: passed and generated release evidence packet
  `release_evidence_e747aba122aa`.

Result:

- Release evidence generation is now a real production acceptance gate, not just
  a report writer.
- `fake-codex` remains available for deterministic regression, but release
  verification can no longer pass solely on fake/offline evidence.
- Current local product acceptance is ready based on recorded real integration
  evidence; current run gates remain action-required until explicitly enabled.

## 2026-06-18 04:02 CST Production Runtime Profile Slice

Branch: `codex/ariadne-production-frontend-integration`

Branch integration decision:

- Re-checked the existing frontend lane against the current production branch.
- Whole-branch integration is still deferred because the frontend lane would
  remove current production backend modules, tests, doctors, evidence commands,
  and roadmap files.
- The current slice stayed in the non-frontend lane and only changed CLI/runtime
  contract plus production docs.

Problem found:

- The product path used real Codex/Claude backends, but several commands and
  docs still relied on manually combining `--planner llm`, `--agent-runtime
  llm`, and `--backlog-planner llm`.
- That made it too easy for a user or future agent to run a real coding backend
  while silently leaving upstream Build Lead / Knowledge / Memory agents and
  feedback backlog planning in deterministic mode.

Implemented:

- Added `--runtime-profile production` to:
  - `ari ticket assign`;
  - `ari ticket run`;
  - `ari daemon run-once`;
  - `ari daemon start`;
  - `ari backend smoke-test`.
- The production profile sets:
  - planner: `llm`;
  - upstream role agent runtime: `llm`;
  - feedback backlog planner: `llm`.
- Kept the default profile as `deterministic` so tests and offline regression
  remain credential-free.
- Added validation for unknown runtime profiles.
- Updated production docs to use `--runtime-profile production` instead of the
  longer manual LLM flag combination.
- Added tests for:
  - direct ticket assignment with production profile;
  - Build Team routing with production profile;
  - invalid profile rejection;
  - active production docs containing the production profile and not the older
    manual flag pair.

Verification so far:

- `python3.11 -m pytest tests/test_agent_teammate_mode.py -q`: passed,
  `18 passed`.
- `python3.11 -m pytest tests/test_agent_teammate_mode.py tests/test_v1_docs.py tests/test_backend_smoke_cli.py -q`:
  passed, `34 passed`.
- `python3.11 -m ruff check ariadne_ltb/cli.py tests/test_agent_teammate_mode.py tests/test_v1_docs.py`:
  passed.
- CLI smoke with a temporary store:
  `ari ticket assign ARI-003 --to codex --runtime-profile production` wrote
  `planner=llm`, `agent runtime=llm`, and `backlog planner=llm`.
- `ari ticket run --help` and `ari backend smoke-test --help` both show
  `--runtime-profile deterministic|production`.
- `python3.11 -m pytest`: passed, `234 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local `.env` was
  reported only as `[REDACTED]`.
- `scripts/verify_v1.sh`: passed and generated release evidence packet
  `release_evidence_090019a68684`.

Result:

- Production runs now have a single stable profile switch for real upstream LLM
  agent behavior.
- Deterministic mode remains explicit and available for offline regression, but
  the recommended product path no longer depends on remembering several
  separate LLM flags.

## 2026-06-18 04:09 CST GitHub Transport Diagnostic Slice

Branch: `codex/ariadne-production-frontend-integration`

Problem found:

- During push, the configured GitHub HTTPS path temporarily failed with
  `LibreSSL SSL_connect: SSL_ERROR_SYSCALL`.
- Bypassing the configured git proxy with `git -c http.proxy=` allowed the push
  to complete.
- Ariadne already reported `github_git_transport`, but it did not record a
  second probe showing whether the failure was caused by the configured proxy
  or by GitHub credentials/network in general.

Implemented:

- Enhanced `github_transport_snapshot` so that when normal git transport fails
  and `http.proxy` or `https.proxy` is configured, Ariadne runs a second
  read-only probe with git proxy disabled.
- Persisted this probe under `direct_without_proxy` in the GitHub transport
  snapshot.
- Added `suggested_fix` when the configured proxy fails but direct transport
  succeeds.
- Updated `ari github doctor` and `ari doctor integrations` output to show:
  - configured git transport status;
  - direct-without-proxy transport status when relevant;
  - proxy repair suggestion when relevant.
- Kept production readiness conservative: the main configured transport still
  determines `github_git_transport`; the direct probe is diagnostic evidence,
  not a silent bypass.

Verification:

- `python3.11 -m pytest tests/test_github_integration.py tests/test_v1_doctor_release.py -q`:
  passed, `23 passed`.
- `python3.11 -m ruff check ariadne_ltb/github_integration.py ariadne_ltb/doctor.py tests/test_github_integration.py tests/test_v1_doctor_release.py`:
  passed.
- `python3.11 -m ariadne_ltb.cli github doctor`: passed locally. Current
  GitHub transport and `gh auth status` are both `ok`; the direct probe is not
  emitted when the configured transport already works.
- `python3.11 -m ariadne_ltb.cli doctor integrations`: passed locally and
  reports GitHub auth/transport `ok`.
- `python3.11 -m pytest`: passed, `235 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local `.env` was
  reported only as `[REDACTED]`.
- `scripts/verify_v1.sh`: passed and generated release evidence packet
  `release_evidence_9a06c467148b`.

Result:

- When GitHub HTTPS transport flakes because of a configured proxy, Ariadne can
  now show whether direct GitHub transport would work and give the operator a
  concrete proxy repair action.

## 2026-06-18 04:22 CST Backlog Preview Apply Slice

Branch: `codex/ariadne-production-frontend-integration`

Decision:

- Deferred direct merge of `codex/ariadne-workbench-frontend-lane` because its
  merge base is old `main`; a direct merge would remove current production
  runtime modules and tests, including LLM agents, GitHub integration, evidence,
  inbox/search, and store doctor code.
- Continued the core production path instead.

Implemented:

- Added typed `BacklogOperation`, `BacklogConflict`, and `BacklogPreview`
  models.
- Added `.ariadne/backlog/previews/*.json` persistence.
- Added source-driven backlog preview generation through
  `generate_source_backlog_preview`.
- Added `apply_backlog_preview`, which:
  - refuses conflicted previews;
  - refuses stale previews when the ticket backlog changed after preview
    creation;
  - is idempotent when a preview was already applied;
  - creates source documents, Build Tickets, Build Packets, BacklogUpdate
    records, and ticket event logs when applied.
- Added CLI:
  - `ari backlog preview --from-source <path>`
  - `ari backlog apply <preview_id>`
- Added board visibility for pending/applied backlog previews and conflicts.

Why this matters:

- Ariadne's differentiator is not only assigning existing tickets to agents.
  It is letting knowledge, feedback, and codebase state update the ticket set.
- Preview/apply turns that update into an auditable local state transition
  instead of an implicit mutation.

Verification:

- `python3.11 -m pytest tests/test_backlog_preview_apply.py -q`: passed,
  `6 passed`.
- `python3.11 -m ruff check ariadne_ltb/backlog.py ariadne_ltb/models.py ariadne_ltb/storage.py ariadne_ltb/cli.py ariadne_ltb/board.py tests/test_backlog_preview_apply.py`:
  passed.
- `python3.11 -m pytest tests/test_backlog_update_loop.py tests/test_true_mvp_product_loop.py tests/test_v1_board_ux.py -q`:
  passed, `36 passed`.
- Temporary-store CLI smoke:
  `ari backlog preview --from-source examples/sources/github_tiny_cli_readme.md`
  followed by `ari backlog apply <preview_id>` and `ari export board`: passed.
- `python3.11 -m pytest`: passed, `241 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local `.env` was
  reported only as `[REDACTED]`.
- `scripts/verify_v1.sh`: passed and generated release evidence packet
  `release_evidence_0177bd37f242`.

Known limitation:

- This slice wires preview/apply for source-driven backlog updates first.
  Review and execution feedback still record direct `BacklogUpdate` entries;
  they should be routed through the same preview/apply mechanism next.

## 2026-06-18 04:27 CST Feedback Backlog Preview Slice

Branch: `codex/ariadne-production-frontend-integration`

Implemented:

- Extended backlog previews beyond source ingest:
  - `generate_review_feedback_preview`
  - `generate_execution_feedback_preview`
- Extended `ari backlog preview` with:
  - `--from-review <review_report_id>`
  - `--from-execution <execution_result_id>`
- Review feedback preview behavior:
  - passing review proposes a `promote_ticket` operation to `done`;
  - non-passing review proposes a `defer_ticket` operation plus repair
    `add_ticket` operations for each required fix.
- Execution feedback preview behavior:
  - successful execution proposes a `promote_ticket` operation to `reviewing`;
  - failed or blocked execution proposes a `defer_ticket` operation plus a
    repair `add_ticket` operation with typed failure metadata.
- Existing source preview/apply behavior remains unchanged.

Why this matters:

- Ariadne's state machine now has a previewable representation for review and
  execution feedback, not only for source ingestion.
- This moves the product closer to the intended loop:
  `execution/review feedback -> update ticket backlog -> assign next agent`.

Verification:

- `python3.11 -m pytest tests/test_backlog_preview_apply.py -q`: passed,
  `9 passed`.
- `python3.11 -m ruff check ariadne_ltb/backlog.py ariadne_ltb/cli.py tests/test_backlog_preview_apply.py`:
  passed.
- `python3.11 -m pytest tests/test_backlog_update_loop.py tests/test_true_mvp_product_loop.py tests/test_v1_board_ux.py -q`:
  passed, `36 passed`.
- Temporary-store CLI smoke:
  `ari backlog preview --from-review review_manual`,
  `ari backlog preview --from-execution execution_manual`, and
  `ari export board`: passed.
- `python3.11 -m pytest`: passed, `244 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local `.env` was
  reported only as `[REDACTED]`.
- `scripts/verify_v1.sh`: passed and generated release evidence packet
  `release_evidence_59072dc92ad0`.
- Release evidence path:
  `.ariadne/evidence/release_evidence_packet.json`.
- Board path:
  `.ariadne/board/index.md`.

Known limitation:

- The full ticket orchestrator still records feedback-driven `BacklogUpdate`
  entries directly. The next slice should either create feedback previews during
  ticket runs or introduce an explicit apply mode so production operators can
  choose preview-only vs preview-and-apply behavior.

## 2026-06-18 04:36 CST Ticket Run Feedback Preview Apply Slice

Branch: `codex/ariadne-production-frontend-integration`

Implemented:

- Connected feedback backlog previews into the normal `TicketRunOrchestrator`
  product loop.
- `ticket run` now generates and applies:
  - an execution feedback `BacklogPreview` after execution result capture;
  - a review feedback `BacklogPreview` after memory/next-ticket direct updates,
    so the preview fingerprint is current before apply.
- `TicketRunResult` now exposes `backlog_preview_ids` alongside
  `backlog_update_ids`.
- `ari ticket run ...` now prints `backlog previews: ...` so the new audit path
  is visible from CLI output.
- `record_feedback_backlog_updates()` now accepts include flags so orchestrator
  can route execution/review feedback through preview/apply while leaving memory
  gap and codebase observation updates on the existing direct path.
- `apply_backlog_preview()` now records `PROMOTE_TICKET` to `done` as a
  `closed` ticket change instead of a generic reprioritization/update.

Why this matters:

- Ariadne's common ticket run path now uses preview/apply for the two feedback
  signals that are already modeled as backlog previews.
- This moves the product loop closer to:
  `execution/review feedback -> preview backlog mutation -> apply mutation ->
  assign next ticket`.

Engineering note:

- The review preview is intentionally generated after memory/next-ticket direct
  backlog updates. `apply_backlog_preview()` rejects stale previews based on the
  ticket backlog fingerprint; generating the review preview after direct
  memory/codebase updates avoids making it stale in the same ticket run.
- Memory gap and codebase observation updates still use the older direct
  `BacklogUpdate` path. They should move to dedicated preview generators in a
  later slice.

Verification:

- `python3.11 -m pytest tests/test_backlog_update_loop.py tests/test_true_mvp_product_loop.py tests/test_backlog_preview_apply.py -q`:
  passed, `39 passed`.
- `python3.11 -m ruff check ariadne_ltb/orchestrator.py ariadne_ltb/backlog.py ariadne_ltb/cli.py tests/test_backlog_update_loop.py tests/test_true_mvp_product_loop.py`:
  passed.
- `python3.11 -m pytest`: passed, `244 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local `.env` was
  reported only as `[REDACTED]`.
- `scripts/verify_v1.sh`: passed and generated release evidence packet
  `release_evidence_17f70be2bdfb`.
- Release evidence path:
  `.ariadne/evidence/release_evidence_packet.json`.
- Board path:
  `.ariadne/board/index.md`.

Known limitation:

- Memory gap and codebase observation backlog mutations are still direct updates.
  The next production slice should add `generate_memory_gap_preview` and
  `generate_codebase_observation_preview`, then let ticket run apply all four
  feedback classes through the same preview/apply mechanism.

## 2026-06-18 04:44 CST Complete Feedback Preview Apply Slice

Branch: `codex/ariadne-production-frontend-integration`

Implemented:

- Added `BacklogOperationType.NO_OP` so preview/apply can record auditable
  no-change feedback decisions without mutating ticket status.
- Added feedback preview generators for the remaining ticket-run feedback
  classes:
  - `generate_memory_gap_preview`
  - `generate_codebase_observation_preview`
- Extended `apply_backlog_preview()` so suggestion-backed preview operations can
  carry `source_document`, `source_packet`, and `suggestion` metadata and still
  materialize Build Packets for generated follow-up tickets.
- Updated `TicketRunOrchestrator` so all four feedback classes now run through
  preview/apply:
  - execution result;
  - memory gap;
  - codebase observation;
  - review feedback.
- Kept `record_feedback_backlog_updates()` for compatibility, but removed it
  from the orchestrator product path.

Why this matters:

- The reusable ticket-run loop now has one auditable mechanism for feedback
  changing the ticket set.
- The product path is now closer to Ariadne's intended state machine:
  `execution/review/memory/codebase feedback -> BacklogPreview -> apply ->
  BacklogUpdate -> next assignment`.

Engineering notes:

- Memory and codebase previews use next-ticket suggestions as their input
  source, preserving existing deterministic follow-up behavior.
- Preview-generated follow-up tickets keep Build Packets, so downstream planner,
  board, and review flows do not lose structured context.
- `NO_OP` operations are excluded from contradictory-operation conflict grouping
  because they are audit records, not competing ticket mutations.

Verification so far:

- `python3.11 -m pytest tests/test_backlog_preview_apply.py tests/test_backlog_update_loop.py tests/test_true_mvp_product_loop.py -q`:
  passed, `41 passed`.
- `python3.11 -m ruff check ariadne_ltb/backlog.py ariadne_ltb/models.py ariadne_ltb/orchestrator.py tests/test_backlog_preview_apply.py tests/test_backlog_update_loop.py`:
  passed.
- `python3.11 -m pytest`: passed, `246 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; local `.env` was
  reported only as `[REDACTED]`.
- `scripts/verify_v1.sh`: passed and generated release evidence packet
  `release_evidence_83f5b272dde6`.
- Release evidence path:
  `.ariadne/evidence/release_evidence_packet.json`.
- Board path:
  `.ariadne/board/index.md`.

Resolved in the following slice:

- `ari backlog preview` currently exposes source/review/execution preview
  commands. Memory-gap and codebase-observation previews are generated through
  ticket runs; the next slice adds explicit artifact-driven preview commands
  for manual preview generation outside `ticket run`.

## 2026-06-18 04:52 CST Artifact-Driven Feedback Preview CLI Slice

Branch: `codex/ariadne-production-frontend-integration`

Implemented:

- Extended `ari backlog preview` with explicit artifact-driven feedback inputs:
  - `--from-memory-gap <ticket_id_or_key>`
  - `--from-codebase-observation <ticket_id_or_key>`
- The CLI now resolves the selected ticket's stored Build Packet, execution
  result, review report, memory record id, and effective next-ticket artifact
  path from ticket metadata, then generates the same backlog previews used by
  `ticket run`.
- Added validation that reports missing feedback artifact metadata instead of
  creating partial or misleading previews.
- Added deterministic CLI tests for memory-gap preview, codebase-observation
  preview, mutually exclusive input validation, and missing metadata reporting.

Why this matters:

- Operators and the frontend can now inspect memory/codebase feedback backlog
  mutations without rerunning the ticket execution loop.
- The ticket-centered state machine is more visible: feedback artifacts can be
  replayed into `BacklogPreview` records before any ticket set mutation is
  applied.

Verification so far:

- `python3.11 -m pytest tests/test_backlog_preview_apply.py`: passed,
  `13 passed`.
- `python3.11 -m ruff check ariadne_ltb/cli.py tests/test_backlog_preview_apply.py`:
  passed.
- `python3.11 -m pytest`: passed, `248 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; DeepSeek key was
  reported as set and `.env` secret findings were redacted.
- `scripts/verify_v1.sh`: passed and generated release evidence packet
  `release_evidence_e740a0dc8f79`.
- `python3.11 -m ariadne_ltb.cli backlog preview --from-memory-gap ARI-003`:
  passed and generated `backlog_preview_95d23db10319`.
- `python3.11 -m ariadne_ltb.cli backlog preview --from-codebase-observation ARI-003`:
  passed and generated `backlog_preview_f1a3eb2a9b26`.

Release evidence path:

- `.ariadne/evidence/release_evidence_packet.json`

Board path:

- `.ariadne/board/index.md`

## 2026-06-18 12:08 CST Supervisor Bounded Loop Slice

Branch: `codex/ariadne-production-frontend-integration`

Implemented:

- Added `supervisor_loop()` in `ariadne_ltb/supervisor.py`.
- Added `ari supervisor loop` as a bounded multi-cycle supervisor command.
- The loop:
  - refreshes inbox evidence each cycle;
  - recovers open inbox items into repair tickets;
  - dispatches repair tickets to an Agent profile;
  - optionally runs one daemon claim/execution per cycle only with
    `--run-daemon`;
  - stops after an idle cycle by default;
  - persists a compact JSON report under `.ariadne/supervisor/`.
- Reused the same run-once summary structure for CLI and Python API output.
- Updated README with the loop command.
- Added deterministic tests for loop recovery/dispatch, idle stop, fixed idle
  cycles, and report persistence.

Safety boundaries:

- The loop does not enable real external execution by itself.
- Codex/Claude execution still requires the existing environment gate and
  `--confirm-execution` when `--run-daemon` is used.
- The persisted report contains counts, ids, statuses, and paths only; it does
  not print or persist credentials.

Verification:

- `python3.11 -m pytest tests/test_supervisor.py`: passed, `5 passed`.
- `python3.11 -m ruff check ariadne_ltb/supervisor.py ariadne_ltb/cli.py tests/test_supervisor.py`: passed.
- `python3.11 -m ariadne_ltb.cli supervisor loop --help`: passed and shows
  bounded loop controls.
- `python3.11 -m pytest`: passed, `263 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; Codex and Claude
  commands were found, DeepSeek key was reported as set, external execution was
  unset, and `.env` secret findings were redacted.
- `scripts/verify_v1.sh`: passed, including release evidence, workbench data
  sync, and `frontend/ariadne-workbench` production build.

Release evidence path:

- `.ariadne/evidence/release_evidence_packet.json`

Board path:

- `.ariadne/board/index.md`

## 2026-06-18 11:36 CST Inbox Recovery Visibility Slice

Branch: `codex/ariadne-production-frontend-integration`

Implemented:

- Extended the board Inbox section with status, severity, source, typed failure
  reason, recommended action, evidence path, resolution note, and generated
  repair ticket key.
- Extended the local workbench sync contract so `.ariadne/inbox/items.json`
  exports recovery fields into `workbench.json`:
  - `ticketKey`
  - `status`
  - `severity`
  - `sourceType`
  - `sourceId`
  - `failureReason`
  - `recommendedAction`
  - `evidenceRef`
  - `resolutionNote`
  - `repairTicketId`
  - `repairTicketKey`
- Updated the current workbench Inbox page to show recovery metadata and to
  navigate to the generated repair ticket when one exists.
- Added deterministic coverage for board inbox repair evidence and workbench
  inbox recovery data export.

Why this matters:

- Inbox recovery was previously functional but under-visible. Failed runs could
  become repair tickets, but the board and web workbench did not show enough
  evidence for a human or supervisor agent to understand what happened.
- This slice makes the failure-to-repair path inspectable:
  failure evidence -> inbox item -> recommended action -> repair ticket ->
  board/workbench visibility.

Verification:

- `python3.11 -m pytest tests/test_v1_board_ux.py tests/test_workbench_data_sync.py`:
  passed, `8 passed`.
- `npm run build` in `frontend/ariadne-workbench`: passed.
- `python3.11 -m pytest`: passed, `254 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; Codex and Claude
  commands were found, DeepSeek key was reported as set, external execution was
  unset, and `.env` secret findings were redacted.
- `scripts/verify_v1.sh`: passed and generated release evidence packet
  `release_evidence_563d10dac2ff`.

Release evidence path:

- `.ariadne/evidence/release_evidence_packet.json`

Board path:

- `.ariadne/board/index.md`

## 2026-06-18 06:18 CST Inbox Recovery Ticket Slice

Branch: `codex/ariadne-production-frontend-integration`

Implemented:

- Added `BacklogUpdateTrigger.INBOX_RECOVERY`.
- Added `create_repair_ticket_from_inbox()` so an inbox item can be promoted
  into a repair Build Ticket through Ariadne's existing BacklogPreview and
  BacklogUpdate audit path.
- Added `ari inbox create-ticket <item_id>`:
  - default behavior writes and applies a repair-ticket preview;
  - `--preview-only` writes the preview without mutating tickets;
  - output supports `table|json`;
  - repeated calls are idempotent and return the existing repair ticket.
- The created repair ticket includes:
  - source document metadata derived from the inbox item;
  - Build Packet creation through the existing preview apply path;
  - metadata linking it back to the inbox item and source failure.
- The source inbox item is marked `acknowledged` after repair-ticket creation.

Why this matters:

- This closes the failure recovery loop:
  real failure -> inbox item -> repair ticket -> backlog update evidence.
- Ariadne can now turn provider/auth/quota/runtime failures into visible work
  instead of leaving them as passive diagnostics or requiring manual ticket
  creation outside the system.

Focused verification:

- `python3.11 -m pytest tests/test_inbox.py`: passed, `6 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m pytest`: passed, `253 passed`.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; Codex and Claude
  commands were found, DeepSeek key was reported as set, external execution was
  unset, and `.env` secret findings were redacted.
- `python3.11 -m ariadne_ltb.cli inbox --help`: passed and shows
  `create-ticket`.
- `scripts/verify_v1.sh`: passed and generated release evidence packet
  `release_evidence_740c8c6554c4`; workbench sync reported 18 inbox items.

Release evidence path:

- `.ariadne/evidence/release_evidence_packet.json`

Board path:

- `.ariadne/board/index.md`

## 2026-06-18 05:52 CST Inbox Resolution Workflow Slice

Branch: `codex/ariadne-production-frontend-integration`

Implemented:

- Extended `InboxItem` with `resolution_note`.
- Added `AriadneStore.load_inbox_item()` and
  `AriadneStore.update_inbox_item_status()` for item-level inbox operations.
- `ari inbox show <item_id>` now displays status, severity, source, failure
  reason, recommended action, evidence reference, and resolution note.
- `ari inbox resolve <item_id> --note ...` marks an inbox item resolved after
  evidence review.
- `ari inbox list` now hides resolved items by default; `--include-resolved`
  shows them for audit.
- `ari inbox refresh` preserves acknowledged/resolved status instead of
  reopening the same materialized failure item.
- Local search now indexes inbox status and resolution note so resolved failure
  decisions remain searchable.

Why this matters:

- Ariadne's production loop now has a basic work-management closure for real
  failures: materialize issue -> inspect evidence -> resolve with note ->
  keep searchable audit history.
- This moves inbox from a passive failure list toward the Multica-style issue
  lifecycle Ariadne needs for real agent workbench usage.

Focused verification:

- `python3.11 -m pytest tests/test_inbox.py`: passed, `4 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m pytest`: passed, `251 passed`.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; Codex and Claude
  commands were found, DeepSeek key was reported as set, external execution was
  unset, and `.env` secret findings were redacted.
- `scripts/verify_v1.sh`: passed and generated release evidence packet
  `release_evidence_0cb0a8ae09f0`; workbench sync reported 18 inbox items.

Release evidence path:

- `.ariadne/evidence/release_evidence_packet.json`

Board path:

- `.ariadne/board/index.md`

## 2026-06-18 05:28 CST AgentRun Failure Inbox/Search Slice

Branch: `codex/ariadne-production-frontend-integration`

Implemented:

- Added `AriadneStore.list_runs()` so product diagnostics can inspect persisted
  AgentRun records without walking private storage paths.
- `ari inbox refresh` now materializes blocked or failed `AgentRun` records as
  `agent_run` inbox items.
- Blocked DeepSeek upstream roles, such as Build Lead, Knowledge, Planner,
  Reviewer, and Memory agent failures, now produce actionable inbox records
  instead of being visible only as artifacts.
- Inbox evidence references the latest run artifact when available, falling
  back to the run JSON record.
- Local search now indexes AgentRun records directly, including role, lifecycle
  state, failure reason, backend, metadata, output summary, and error text.

Why this matters:

- The production workbench path depends on real upstream LLM agents. Provider
  failures, invalid JSON, schema validation failures, and role-level blockers
  must become visible work-management items, not hidden logs.
- This closes a diagnostic gap in the loop:
  real LLM agent failure -> AgentRun blocked -> inbox item -> searchable
  evidence -> board/release evidence can surface the issue.

Focused verification:

- `python3.11 -m pytest tests/test_inbox.py tests/test_local_search.py`:
  passed, `6 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m pytest`: passed, `250 passed`.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; Codex and Claude
  commands were found, DeepSeek key was reported as set, external execution was
  unset, and `.env` secret findings were redacted.
- `scripts/verify_v1.sh`: passed and generated release evidence packet
  `release_evidence_e42b5f85a8c8`; workbench data sync reported 18 inbox items.

Release evidence path:

- `.ariadne/evidence/release_evidence_packet.json`

Board path:

- `.ariadne/board/index.md`

## 2026-06-18 04:57 CST Workbench Backlog Preview Data Contract Slice

Branch: `codex/ariadne-production-frontend-integration`

Implemented:

- Updated the local workbench data sync contract so it reads real
  `.ariadne/backlog/previews/*.json` records.
- `frontend/ariadne-workbench/public/web_data/workbench.json` now derives
  `backlogChanges` from `BacklogPreview.operations` when previews exist, instead
  of only inferring changes from `next_tickets.json`.
- Extended synced backlog change records with preview evidence:
  - `previewId`
  - `previewStatus`
  - `triggerType`
  - `operationType`
  - `appliedUpdateId`
  - `conflictCount`
  - `evidenceRefs`
- Extended `backlogMutationPreview` with latest preview id, trigger type, and
  applied update id.
- Preserved `no_op` preview operations as explicit `no_op` records instead of
  mislabeling them as rejected ticket changes.
- Kept the existing next-ticket-derived fallback when no backlog previews exist.

Why this matters:

- The frontend/workbench data contract now consumes Ariadne's real ticket
  state-machine evidence instead of an approximation.
- Operators can inspect whether backlog mutations are preview-only, applied, or
  blocked without reading raw JSON files.
- This supports the production target:
  `feedback/codebase -> BacklogPreview -> BacklogUpdate -> visible workbench`.

Verification so far:

- `python3.11 -m pytest tests/test_workbench_data_sync.py`: passed.
- `npm run build` in `frontend/ariadne-workbench`: passed.
- `npm run sync:data` in `frontend/ariadne-workbench`: passed and produced
  local workbench data with `previewId`, `triggerType`, `operationType`, and
  `appliedUpdateId` fields.
- Local workbench JSON inspection confirmed `no_op` preview operations remain
  `no_op` (`noOps=32`, `rejected=0`).
- `python3.11 -m pytest`: passed, `248 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; DeepSeek key was
  reported as set and `.env` secret findings were redacted.
- `scripts/verify_v1.sh`: passed and generated release evidence packet
  `release_evidence_c1f6d67c170e`.

Release evidence path:

- `.ariadne/evidence/release_evidence_packet.json`

Board path:

- `.ariadne/board/index.md`

Frontend integration decision:

- The separate `codex/ariadne-workbench-frontend-lane` branch remains clean and
  unmerged into this core branch.
- This slice changed only the backend-to-workbench data contract already present
  on the core branch. Full frontend branch integration is still deferred until
  the core production data contract settles or a merge is explicitly required.

## 2026-06-18 05:05 CST Workbench Product Readiness Evidence Slice

Branch: `codex/ariadne-production-frontend-integration`

Frontend integration decision:

- Rechecked `codex/ariadne-workbench-frontend-lane` against this core branch.
- Direct merge remains unsafe because that lane is behind the current production
  backend and would remove many core modules, docs, and tests added by the real
  DeepSeek, Codex, Claude Code, Feishu, GitHub, inbox, evidence, and backlog
  preview slices.
- Continued on the core production branch and changed only the workbench data
  contract plus its current release evidence panel.

Implemented:

- Extended `releaseEvidence` in the local workbench data contract with:
  - `productReadinessChecks`
  - `realSuccessEvidence`
  - `realFailureEvidence`
  - `evidenceRefs`
  - ticket, execution, review, and inbox counts
- Updated the current workbench Release packet panel to show:
  - ready check count;
  - real success/failure evidence count;
  - execution count;
  - the first readiness checks.
- Added deterministic sync coverage proving release evidence checks and
  real-success/failure evidence are exported to workbench JSON.

Why this matters:

- The workbench can now inspect production acceptance evidence directly instead
  of seeing only a coarse `ready/action_required` summary.
- This makes Ariadne's product path more reviewable:
  real integrations -> release evidence packet -> product readiness checks ->
  visible workbench state.

Verification:

- `python3.11 -m pytest tests/test_workbench_data_sync.py`: passed.
- `npm run build` in `frontend/ariadne-workbench`: passed.
- `npm run sync:data` in `frontend/ariadne-workbench`: passed and produced
  workbench data containing product readiness checks, real success/failure
  evidence, evidence refs, and counts.
- `python3.11 -m pytest`: passed, `248 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; Codex and Claude
  commands were found, DeepSeek key was reported as set, external execution was
  unset, and `.env` secret findings were redacted.
- `scripts/verify_v1.sh`: passed and generated release evidence packet
  `release_evidence_96063902d1d7`.

Release evidence path:

- `.ariadne/evidence/release_evidence_packet.json`

Board path:

- `.ariadne/board/index.md`

## 2026-06-18 11:36 CST Bulk Inbox Recovery Slice

Branch: `codex/ariadne-production-frontend-integration`

Implemented:

- Added `recover_inbox_items()` for batch inbox recovery.
- Added `ari inbox recover` so a supervisor can convert actionable open inbox
  items into repair Build Tickets through the existing backlog preview/apply
  path.
- Added recovery controls:
  - `--preview-only` writes repair previews without mutating tickets;
  - `--include-acknowledged` confirms previously acknowledged failures still
    point at existing repair tickets;
  - `--no-refresh` uses the current inbox snapshot;
  - `--limit` caps one supervisor pass.
- Updated README inbox guidance so future agents see batch recovery as the
  normal recovery path, not only single-item `create-ticket`.
- Added deterministic tests for batch creation, idempotent acknowledged-item
  recovery, preview-only mode, and limit handling.

Why this matters:

- Ariadne already materialized failures into inbox items and could create one
  repair ticket at a time. That was too manual for the supervisor / overnight
  workflow.
- This slice makes feedback-to-ticket recovery operational:
  inbox failures -> batch recovery -> repair tickets -> backlog update evidence.

Verification:

- `python3.11 -m pytest tests/test_inbox.py`: passed, `8 passed`.
- `python3.11 -m ariadne_ltb.cli inbox --help`: passed and shows `recover`.
- `python3.11 -m ariadne_ltb.cli inbox recover --help`: passed and shows batch
  recovery options.

- `python3.11 -m pytest`: passed, `256 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; Codex and Claude
  commands were found, DeepSeek key was reported as set, external execution was
  unset, and `.env` secret findings were redacted.
- `scripts/verify_v1.sh`: passed and generated release evidence packet
  `release_evidence_ad42d6f0a742`.

Release evidence path:

- `.ariadne/evidence/release_evidence_packet.json`

Board path:

- `.ariadne/board/index.md`

## 2026-06-18 11:36 CST Inbox Repair Dispatch Slice

Branch: `codex/ariadne-production-frontend-integration`

Implemented:

- Added `dispatch_repair_tickets()` to assign inbox-generated repair tickets to
  Agent profiles without duplicating open assignments.
- Added `ari inbox dispatch-repairs`:
  - defaults to `--to codex --runtime-profile production`;
  - supports backend/planner/agent-runtime/backlog-planner overrides;
  - supports `--limit` for bounded supervisor passes;
  - emits `table|json` summaries for automation.
- Dispatch skips repair tickets that are already done/cancelled/superseded or
  already have queued/claimed/running assignments.
- Updated README to show the operational chain:
  `inbox refresh -> inbox recover -> inbox dispatch-repairs -> daemon run-once`.
- Added deterministic tests for fake-codex dispatch idempotency and production
  Codex/LLM assignment defaults.

Why this matters:

- Batch recovery created repair Build Tickets, but those tickets still needed a
  manual assignment step before the daemon/runtime could claim them.
- This slice connects feedback recovery to the Agent queue:
  inbox failure -> repair ticket -> assignment -> daemon/runtime.

Verification:

- `python3.11 -m pytest tests/test_inbox.py`: passed, `10 passed`.
- `python3.11 -m ruff check ariadne_ltb/inbox.py ariadne_ltb/cli.py tests/test_inbox.py`: passed.
- `python3.11 -m ariadne_ltb.cli inbox --help`: passed and shows `dispatch-repairs`.
- `python3.11 -m ariadne_ltb.cli inbox dispatch-repairs --help`: passed and shows
  production defaults and dispatch options.

- `python3.11 -m pytest`: passed, `258 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; Codex and Claude
  commands were found, DeepSeek key was reported as set, external execution was
  unset, and `.env` secret findings were redacted.
- `scripts/verify_v1.sh`: passed and generated release evidence packet
  `release_evidence_09d56fe08564`.

Release evidence path:

- `.ariadne/evidence/release_evidence_packet.json`

Board path:

- `.ariadne/board/index.md`

## 2026-06-18 11:36 CST Supervisor Run Once Slice

Branch: `codex/ariadne-production-frontend-integration`

Implemented:

- Added `ariadne_ltb/supervisor.py` with `supervisor_run_once()`.
- Added `ari supervisor run-once` as a bounded local supervisor pass:
  - refresh inbox evidence;
  - recover open inbox items into repair tickets;
  - dispatch repair tickets to an Agent profile;
  - optionally run one daemon claim/execution only when `--run-daemon` is set.
- The default command is production-oriented but safety-gated:
  - default agent is `codex`;
  - default runtime profile is `production`;
  - daemon execution is skipped unless explicitly requested;
  - real external execution still requires the normal `--confirm-execution` and
    environment gate when daemon execution reaches Codex or Claude.
- Updated README with the supervisor recovery path.
- Added deterministic supervisor tests for recovery+dispatch without daemon,
  skip flags, and daemon polling with no work.

Why this matters:

- Previous slices gave Ariadne the pieces: inbox refresh, batch recover, repair
  dispatch, and daemon run-once. Users and automation still had to remember the
  sequence manually.
- This slice gives Ariadne a local supervisor entrypoint for the production
  workbench loop:
  failure evidence -> inbox -> repair ticket -> assignment queue -> optional
  daemon/runtime.

Verification:

- `python3.11 -m pytest tests/test_supervisor.py`: passed, `3 passed`.
- `python3.11 -m ruff check ariadne_ltb/supervisor.py ariadne_ltb/cli.py tests/test_supervisor.py`: passed.
- `python3.11 -m ariadne_ltb.cli supervisor --help`: passed and shows `run-once`.
- `python3.11 -m ariadne_ltb.cli supervisor run-once --help`: passed and shows
  recovery, dispatch, daemon, and production profile options.

- `python3.11 -m pytest`: passed, `261 passed`.
- `python3.11 -m ruff check .`: passed.
- `python3.11 -m ariadne_ltb.cli demo full`: passed.
- `python3.11 -m ariadne_ltb.cli export board`: passed.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed; Codex and Claude
  commands were found, DeepSeek key was reported as set, external execution was
  unset, and `.env` secret findings were redacted.
- `scripts/verify_v1.sh`: passed and generated release evidence packet
  `release_evidence_494eaa10903d`.

Release evidence path:

- `.ariadne/evidence/release_evidence_packet.json`

Board path:

- `.ariadne/board/index.md`
