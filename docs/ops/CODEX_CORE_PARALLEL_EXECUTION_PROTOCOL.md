# Codex Core Parallel Execution Protocol

Status: superseded

Superseded by:

```text
docs/goals/2026-06-17-2043-ariadne-production-agent-workbench-goal.md
docs/superpowers/plans/2026-06-17-2043-ariadne-production-agent-workbench-execution-plan.md
```

Reason: this protocol was written for a non-frontend core section. The active
direction is now production-first and should not treat fake-codex/demo work as
the product path.

This file is separate from the shared sprint plan and from the frontend
section's plan. The frontend section may continue to use its current document.
This protocol only governs the current section that owns Ariadne core,
runtime, orchestration, backends, safety, CLI, board data, and tests.

## Purpose

Increase implementation throughput without turning Ariadne development into
uncontrolled parallel edits.

The target is:

```text
Codex main section
  -> owns final design, edits, tests, commits, pushes, and Multica updates
  -> uses subagents for independent investigation, review, and narrow patches
  -> keeps frontend work isolated in the frontend section
```

Parallelism is useful only when the work items have clear ownership boundaries.
If two agents edit the same core files at the same time, the likely result is
merge churn, weaker review, and slower delivery.

## Current Section Ownership

This section owns everything except frontend implementation:

- domain models and lifecycle invariants;
- store, JSON/JSONL persistence, migrations, and doctors;
- ticket, assignment, daemon, run, and runtime orchestration;
- execution backends and provider capability reporting;
- planner, memory, review, Feishu dry-run, route decisions, next tickets;
- CLI product paths;
- board data and static board export;
- safety gates, prompt-injection checks, secret checks, target path validation;
- test coverage, release checks, development report, and Multica progress.

This section must not own:

- React or Next.js frontend screens;
- visual design implementation;
- browser UI routing and client state;
- frontend-only CSS or component polish.

When frontend needs data, this section exposes stable models, CLI output, or
`.ariadne/` artifacts. The frontend section consumes those contracts.

## Parallel Lanes

Use these lanes to decide whether work can run concurrently.

### Lane 1: Store and State Integrity

Files usually touched:

- `ariadne_ltb/models.py`
- `ariadne_ltb/storage.py`
- `ariadne_ltb/store_doctor.py`
- `tests/test_store_doctor.py`
- `tests/test_*store*.py`

Good subagent tasks:

- inspect invariant gaps;
- design typed failure reasons;
- add focused fixtures;
- review state transition bugs.

Avoid parallel edits with Lane 2 when both touch assignment state.

### Lane 2: Assignment, Daemon, and Runtime

Files usually touched:

- `ariadne_ltb/daemon.py`
- `ariadne_ltb/runtime.py`
- `ariadne_ltb/orchestrator.py`
- `ariadne_ltb/failure.py`
- `tests/test_daemon*.py`
- `tests/test_assignment*.py`
- `tests/test_failure*.py`

Good subagent tasks:

- review claim and lease behavior;
- simulate stale lease and blocked assignment paths;
- propose recovery rules;
- inspect progress event coverage.

Avoid parallel edits with Lane 3 when both touch execution result lifecycle.

### Lane 3: Backends and Execution Safety

Files usually touched:

- `ariadne_ltb/backends.py`
- `ariadne_ltb/backend_doctor.py`
- `ariadne_ltb/security.py`
- `ariadne_ltb/orchestrator.py`
- `tests/test_backends.py`
- `tests/test_backend_doctor.py`

Good subagent tasks:

- audit Codex/Claude command rendering;
- test disabled external execution paths;
- inspect secret and prompt-injection guard behavior;
- compare backend output with board evidence.

Avoid real external execution unless the user explicitly confirms it and the
required environment gate is set.

### Lane 4: Knowledge, Planner, and Backlog Update

Files usually touched:

- `ariadne_ltb/ingest.py`
- `ariadne_ltb/planner.py`
- `ariadne_ltb/backlog.py`
- `ariadne_ltb/memory.py`
- `tests/test_ingest*.py`
- `tests/test_planner*.py`
- `tests/test_backlog*.py`

Good subagent tasks:

- inspect source evidence extraction;
- review next-ticket generation quality;
- test supersede, downgrade, split, and follow-up paths;
- ensure Goal remains input metadata, not the center object.

### Lane 5: CLI, Board Data, and Release Evidence

Files usually touched:

- `ariadne_ltb/cli.py`
- `ariadne_ltb/board.py`
- `scripts/verify_v1.sh`
- `README.md`
- `docs/development_report.md`
- `docs/ops/*.md`
- `tests/test_cli*.py`
- `tests/test_board*.py`

Good subagent tasks:

- check command UX and output determinism;
- verify board sections include evidence links;
- review release script drift;
- inspect docs for wrong Goal-centered language.

This lane can usually run after another lane produces data artifacts.

## Subagent Use Pattern

Use subagents for bounded work that can be reviewed and merged by the main
Codex section.

Preferred task shapes:

- "inspect these files and list concrete risks";
- "write a minimal failing test for this invariant";
- "review this diff for regressions";
- "prototype a small isolated helper without touching shared lifecycle files";
- "compare board output before and after this change".

Avoid giving subagents broad ownership such as:

- "implement the runtime";
- "rewrite the orchestrator";
- "fix all tests";
- "do the backend work";
- "clean up architecture".

The main section remains responsible for:

- final architecture decisions;
- conflict resolution;
- editing shared files;
- running full verification;
- committing and pushing;
- Multica status updates.

## Worktree Rule

For high-risk or broad edits, create a separate worktree per lane:

```bash
git worktree add ../Ariadne.worktrees/<lane-branch> -b codex/<lane-branch>
```

Use one worktree when the slice is narrow and the touched files are known. Use
multiple worktrees only when two lanes can run without overlapping files.

Do not let two active worktrees edit the same file family unless the main
section has explicitly sequenced the merge order.

Recommended branch naming:

```text
codex/core-store-integrity-<n>
codex/core-runtime-assignment-<n>
codex/core-backend-safety-<n>
codex/core-knowledge-backlog-<n>
codex/core-cli-board-release-<n>
```

## File Ownership Lock

Before starting a slice, declare the expected touched file set in the section
notes or Multica comment.

Example:

```text
LOC-8 run message stream
Owned files:
- ariadne_ltb/models.py
- ariadne_ltb/storage.py
- ariadne_ltb/orchestrator.py
- ariadne_ltb/planner.py
- ariadne_ltb/runtime.py
- ariadne_ltb/cli.py
- ariadne_ltb/board.py
- tests/test_run_messages.py
```

If another section needs one of those files, it should wait or request a data
contract instead of editing the same file.

## Safe Concurrency Level

Use this practical cap:

```text
1 main Codex integrator
2-3 subagents for investigation/review/narrow tests
1 frontend section in separate branch/worktree
```

Do not run five broad implementers against the same Python package. Ariadne's
core is compact, so file contention becomes the bottleneck before LLM token
capacity does.

## Integration Cadence

For each core slice:

1. Select one Multica issue or one coherent local slice.
2. Declare owned files.
3. Ask subagents for review or test design only when the slice has independent
   questions.
4. Main section implements the final patch.
5. Run focused tests.
6. Run full verification:

```bash
python3.11 -m pytest
python3.11 -m ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
python3.11 -m ariadne_ltb.cli doctor store
scripts/verify_v1.sh
```

7. Commit and push the slice.
8. Write Chinese progress to Multica with files changed, commands run, and
   result.
9. Mark the issue done only after verification passes.

## When to Increase Parallelism

Increase parallelism when:

- there are independent lanes with non-overlapping files;
- the next task is investigation-heavy;
- failing tests need diagnosis while implementation continues elsewhere;
- frontend only needs a stable artifact schema from core.

Do not increase parallelism when:

- the next change touches `models.py`, `storage.py`, and `orchestrator.py`
  together;
- tests are already failing on the integration branch;
- the branch has uncommitted changes;
- a prior subagent result has not been reviewed.

## Current Recommended Flow

For the current core section:

```text
Main Codex:
  LOC-8 Run message stream implementation and integration

Subagent A:
  Review AgentRun/run storage lifecycle and propose message stream invariants

Subagent B:
  Review CLI and board expectations for incremental run messages

Subagent C:
  Review tests after implementation for missing edge cases

Frontend section:
  Continue independently; consume `.ariadne/` artifacts only after core commits
  and pushes a stable contract
```

This keeps the frontend section moving while the current section strengthens the
runtime and backend architecture underneath it.

## Decision Rule

If a task changes product behavior, the main Codex section implements and owns
the final diff.

If a task asks "is this correct?", "what could break?", or "what tests are
missing?", subagents can do it in parallel.

If a task requires frontend rendering, leave it to the frontend section unless
the missing piece is a backend artifact contract.
