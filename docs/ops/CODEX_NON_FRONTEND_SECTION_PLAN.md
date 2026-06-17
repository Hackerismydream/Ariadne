# Codex Non-Frontend Section Plan

Status: superseded

Superseded by:

```text
docs/goals/2026-06-17-2043-ariadne-production-agent-workbench-goal.md
docs/superpowers/plans/2026-06-17-2043-ariadne-production-agent-workbench-execution-plan.md
```

Reason: this plan preserved a non-frontend, fake-codex-tolerant execution
model. The active direction is now production-first: real DeepSeek upstream LLM
runtime, real Codex, real Claude Code, gated real Feishu writes, and real
GitHub integration.

This document is intentionally new. Do not append this content to the shared
v1.0 sprint plan or to any frontend section plan. The frontend section may keep
referencing its existing plan without absorbing this section's execution rules.

## Mission

This section owns every Ariadne workstream except frontend implementation.

The target is to make Ariadne reach Multica-level agent work-management
maturity while staying local-first, Python-based, single-user, deterministic,
and safety-gated.

The product loop remains:

```text
Knowledge / Feedback / Codebase
  -> update Ticket backlog
  -> Ticket management center
  -> assign to Agent
  -> local Daemon / Runtime
  -> Codex / Claude / fake-codex
  -> Review / Comments / Board / Memory
  -> update Ticket backlog again
```

Goal can be input context. Goal is not the center object. Build Ticket,
Assignment, Run, Comment, Review, Memory, and Backlog Update are the runtime
work objects.

## Ownership

This section owns:

- domain models and lifecycle invariants;
- ticket, assignment, run, artifact, comment, review, memory, and backlog
  persistence;
- source ingestion, planner, Build Packet generation, and evidence quality;
- backlog update engine driven by knowledge, feedback, memory, and codebase
  observations;
- local daemon, assignment claiming, heartbeat, locking, retries, and recovery;
- agent runtime surfaces, run messages, progress events, and comments;
- execution backends: `fake-codex`, real `codex`, `claude-code`, `shell`, and
  dry-run scaffolds;
- provider capability, backend doctor, store doctor, secret doctor, release
  doctor, and safety gates;
- handoff generation, skill materialization, route decisions, and permission
  profiles;
- reviewer, verifier, memory write-back, Feishu dry-run plans, and next-ticket
  generation;
- static board data and board export;
- CLI product paths and machine-readable outputs consumed by other sections;
- tests, verification scripts, release evidence, development reports, commits,
  pushes, and Multica progress comments.

This section does not own:

- React or Next.js frontend implementation;
- visual design, browser layout, component styling, or client state;
- hosted auth, multi-tenant SaaS workspace, WebSocket collaboration, or a
  production server platform;
- real Feishu writes by default;
- auto-merge or auto-deploy behavior inside Ariadne runtime.

If frontend work needs a backend field, this section should add a typed model,
persisted artifact, CLI JSON output, or board data contract. It should not make
frontend-only ad hoc files.

## Workstreams

### 1. Store and Domain Integrity

Purpose: make local JSON/JSONL state reliable enough for long-running agent
work.

Scope:

- lifecycle-state invariants for tickets, assignments, and runs;
- typed failure reasons;
- duplicate key detection;
- orphan and missing-reference detection;
- malformed JSON and JSONL detection;
- stale lock and stale lease reporting;
- migration-safe readers for older artifacts.

Done means:

- `python3.11 -m ariadne_ltb.cli doctor store` is deterministic;
- invalid fixtures produce typed evidence;
- release verification can trust the store before running agents.

### 2. Assignment, Daemon, and Runtime

Purpose: make Ariadne behave like a local agent workbench, not a one-shot demo.

Scope:

- assignment queue and claim rules;
- local daemon run-once and future loop mode;
- heartbeat and lease expiry;
- target repo locking;
- retry queue and repair policy;
- run message stream;
- progress events and thread-aware comments;
- safe resume after interrupted runs.

Done means:

- `ari daemon run-once` can claim, run, review, and finalize a ticket;
- stale or failed work produces visible recovery instructions;
- no two assignments can safely mutate the same target repo at the same time.

### 3. Orchestrator and Backends

Purpose: keep `ticket run` as the reusable full loop and make every backend
observable, gated, and reviewable.

Scope:

- `TicketRunOrchestrator` result manifest completeness;
- handoff generation;
- route decision artifact;
- backend preflight;
- external execution gates;
- Codex and Claude command-template rendering;
- stdout, stderr, exit code, test output, git diff, and changed-file capture;
- backend capability snapshots;
- permission profiles and target path validation.

Done means:

- `ari ticket run ARI-003 --backend fake-codex` completes the full loop;
- real Codex/Claude remain blocked unless both env gate and explicit
  confirmation are present;
- backend doctor never prints secrets.

### 4. Knowledge, Planner, and Backlog Update

Purpose: make Ariadne's unique loop real: new knowledge and execution feedback
change the ticket set before agents continue work.

Scope:

- source ingestion evidence extraction;
- deterministic planner;
- optional LLM planner with safe failure;
- memory retrieval hooks;
- review-driven next-ticket generation;
- backlog update records;
- create, update, downgrade, supersede, split, and no-op decisions;
- rationale and evidence for every ticket-set change.

Done means:

- external sources can create or update tickets with evidence;
- completed runs can generate follow-up tickets from review, memory, and code
  observations;
- `ari backlog history` and the board explain why the backlog changed.

### 5. Safety, Verification, and Release Evidence

Purpose: keep autonomy useful without letting agents damage user state or hide
bad results.

Scope:

- `.gitignore` and secret safety;
- prompt-injection guard;
- external execution gates;
- Feishu write gates;
- target repo validation;
- release checklist and verification script;
- development report updates.

Done means:

- tests require no network, Codex, Claude, DeepSeek, Feishu, or GitHub token;
- `python3.11 -m pytest`, `python3.11 -m ruff check .`, demo, board export,
  backend doctor, and `scripts/verify_v1.sh` pass before each code slice lands;
- blocked states contain exact evidence.

## Parallelism Rules

Use this section as the main integrator. Subagents are useful for review,
investigation, narrow tests, and isolated helper implementation. They are not
the final owner of broad runtime or orchestrator changes.

Safe parallelism:

```text
1 main Codex integrator for final edits, tests, commits, pushes
2-3 subagents for bounded review or narrow patches
1 separate frontend section in its own branch/worktree
```

Do not run multiple broad implementers against the same Python files. Ariadne's
core is compact; file contention will slow the work more than extra tokens help.

Before starting a slice, declare the expected touched file set in the Multica
comment or local progress note. If a frontend section needs the same file, this
section should provide a stable data contract and let frontend consume it later.

## Frontend Interface Contract

The frontend section should consume stable artifacts, not scrape prose.

Preferred contracts:

- `.ariadne/tickets/*.json`;
- `.ariadne/assignments/*.json`;
- `.ariadne/runs/*.json`;
- `.ariadne/runs/<run_id>/messages.jsonl`;
- `.ariadne/artifacts/<ticket_id>/...`;
- `.ariadne/memory/...`;
- `.ariadne/board/`;
- runtime capability snapshots;
- route decisions;
- progress events;
- doctor reports;
- CLI `--json` output where available.

If a frontend view needs information not present here, add it to the core model
and persistence layer first.

## Work Selection

Pick work in this order:

1. failures that break tests, demo, board export, backend doctor, or release
   verification;
2. store and safety correctness;
3. runtime and assignment reliability;
4. orchestrator and backend observability;
5. knowledge-to-ticket and feedback-to-ticket update quality;
6. frontend-facing data contracts;
7. docs and release evidence.

Do not select frontend-only issues in this section. If a Multica issue mixes
frontend and backend work, split it: this section lands the data/artifact
contract, and the frontend section implements the UI.

## Verification Rule

For every non-doc code slice, run:

```bash
python3.11 -m pytest
python3.11 -m ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
scripts/verify_v1.sh
```

For docs-only changes, run at minimum:

```bash
git diff --check
git status --short
```

## Commit, Push, and Multica Updates

Each coherent slice should end as a reviewable unit:

1. implement;
2. run focused tests;
3. run full verification when code changed;
4. update `docs/development_report.md` when behavior changed;
5. commit;
6. push;
7. write a Chinese Multica comment with files changed, commands run, result,
   and known limits;
8. mark the issue done only after verification passes.

Do not claim success for real Codex, Claude, Feishu, or external execution
unless the run actually happened and the result is recorded.

## Goal Prompt for This Section

Use this prompt when starting or resuming a Codex goal for this section:

```text
You are Codex working on Ariadne's non-frontend core section.

Follow docs/ops/CODEX_NON_FRONTEND_SECTION_PLAN.md.

Do not append to the shared v1.0 sprint plan and do not modify the frontend
section's plan. The frontend section is separate and may continue consuming its
own document.

Your ownership is every non-frontend part of Ariadne: domain models, local
store, ticket lifecycle, assignment queue, daemon, runtime locking, run
messages, comments, backends, orchestrator, planner, memory, review, backlog
updates, board data, CLI, safety doctors, tests, release verification, commits,
pushes, and Multica progress comments.

Keep Ariadne local-first and ticket-centered. Goal can be input context, but
Ticket is the runtime center. Align with Multica's issue-agent-runtime-board
work-management model without copying Multica's hosted server architecture.

Work in small vertical slices. For each slice: inspect current code, declare
owned files, use subagents only for bounded review or narrow tasks, implement,
run verification, commit, push, and write Chinese Multica progress.

Do not touch frontend-only issues unless extracting a backend data contract
needed by the frontend section.
```
