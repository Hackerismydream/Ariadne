# Codex Core Section Execution Plan

Status: superseded

Superseded by:

```text
docs/goals/2026-06-17-2043-ariadne-production-agent-workbench-goal.md
docs/superpowers/plans/2026-06-17-2043-ariadne-production-agent-workbench-execution-plan.md
```

Reason: this plan kept the earlier core/backend/runtime section boundary. The
active direction is now production-first and requires real DeepSeek, Codex,
Claude Code, Feishu, and GitHub integrations where configured.

This document is intentionally separate from the shared v1.0 sprint plan. The
frontend section may keep using the existing plan without having its context
changed by this section.

## Purpose

This section owns all non-frontend work needed to make Ariadne reach a
Multica-aligned local workbench maturity level.

The north star is:

```text
Ariadne = local-first Ticket-centered Agent Workbench

Knowledge / Feedback / Codebase
  -> update Ticket backlog
  -> Ticket management center
  -> assign to Agent
  -> local Daemon / Runtime
  -> Codex / Claude / fake-codex
  -> Review / Comments / Board / Memory
  -> update Ticket backlog again
```

The frontend section may build a richer UI on top of this. This section must
make the underlying local kernel, runtime, backends, artifacts, and CLI stable
enough that the frontend can consume them without guessing.

## Ownership Boundary

This section owns:

- domain models and lifecycle invariants;
- ticket, assignment, run, handoff, review, memory, comment, and artifact
  persistence;
- source ingestion and backlog update logic;
- planner and Build Packet quality;
- local daemon, heartbeat, locking, retry, and recovery;
- backend execution adapters for `fake-codex`, `codex`, `claude-code`, `shell`,
  and dry-run;
- provider capability and safety gating;
- secret, prompt-injection, permission, and store-invariant doctors;
- board data sections and static board export;
- CLI product paths;
- tests, release checks, and development report updates.

This section does not own:

- React, Next.js, or browser UI implementation;
- production hosted auth, workspace tenancy, WebSocket collaboration, or a
  remote server platform;
- visual design polish;
- real Feishu writes by default;
- auto-merge inside Ariadne runtime.

The only frontend-facing responsibility here is to keep CLI output and
`.ariadne/` artifacts predictable, typed, and documented.

## Parallel Work Lanes

Use subagents for independent review, design checks, and implementation
assistance, but keep final integration in this section. Each lane should land
as a self-contained commit with tests.

### Lane A: State and Store Integrity

Goal: make the local JSON/JSONL store trustworthy before agents depend on it.

Scope:

- store invariant doctor;
- duplicate ticket key detection;
- orphan artifact detection;
- malformed JSON and JSONL detection;
- broken ticket, assignment, run, handoff, memory, and artifact references;
- AgentRun lifecycle terminal-state invariants;
- stale lock reporting;
- machine-readable and human-readable doctor reports.

Acceptance:

- `python3.11 -m ariadne_ltb.cli doctor store` reports a clean valid workspace;
- invalid fixtures fail deterministically with typed reasons;
- board shows state integrity evidence.

### Lane B: Runtime and Assignment Reliability

Goal: make Ariadne behave like a local agent work-management runtime, not a
single demo command.

Scope:

- assignment queue correctness;
- daemon claim and heartbeat behavior;
- directory lock behavior;
- retry queue and recovery plans;
- progress events and comments;
- safe resume after interrupted runs;
- no double-claiming on the same target repo.

Acceptance:

- `daemon run-once` can claim and execute an assignment;
- stale or blocked assignments produce explicit recovery evidence;
- `scripts/verify_v1.sh` remains green.

### Lane C: Orchestrator and Backends

Goal: keep `ticket run` as the reusable full loop and make backend behavior
observable, gated, and reviewable.

Scope:

- `TicketRunOrchestrator` result manifest completeness;
- execution permission profiles;
- CodexBackend and ClaudeCodeBackend command-template rendering;
- external execution gating;
- stdout, stderr, exit code, test result, diff, and changed-file capture;
- backend preflight blocking for sensitive files and invalid scopes;
- provider capability snapshot persistence.

Acceptance:

- `ticket run ARI-003 --backend fake-codex` completes the full loop;
- real Codex/Claude paths remain blocked unless explicitly enabled and
  confirmed;
- backend doctor never prints secrets.

### Lane D: Knowledge, Planner, and Backlog Update Loop

Goal: make external knowledge and execution feedback update the ticket set
instead of rewriting a single goal.

Scope:

- source ingestion evidence extraction;
- planner mode and Build Packet quality;
- memory retrieval hooks;
- review-driven next ticket generation;
- backlog update artifacts;
- ticket downgrade, supersede, split, and follow-up decisions.

Acceptance:

- new knowledge can generate or update tickets with evidence;
- completed runs can create next tickets from review and memory;
- board shows why the backlog changed.

### Lane E: Safety and Release Readiness

Goal: keep local autonomy useful without letting agents damage user state or
commit secrets.

Scope:

- secret safety doctor;
- prompt injection guard;
- target repo validation;
- permission profiles;
- `.gitignore` safety;
- release doctor;
- verification script maintenance.

Acceptance:

- `doctor secrets`, `backend doctor`, `doctor v1`, and the release script pass;
- tests require no network, Codex, Claude, DeepSeek, Feishu, or GitHub token;
- safety failures are typed and visible.

## Frontend Interface Contract

The frontend section should not scrape CLI prose as its primary interface. This
section should expose stable files under `.ariadne/`:

- tickets: `.ariadne/tickets/*.json`;
- assignments: `.ariadne/assignments/*.json`;
- runs: `.ariadne/runs/*.json`;
- artifacts: `.ariadne/artifacts/<ticket_id>/...`;
- memory: `.ariadne/memory/...`;
- board export: `.ariadne/board/`;
- runtime capability snapshots;
- route decisions;
- progress events;
- doctor reports.

If the frontend needs another field, add it to the typed model and persist it
through the store. Do not add frontend-only ad hoc files unless they are also
useful as local review artifacts.

## Work Selection Rule

Prioritize work in this order:

1. blockers that prevent current tests, demo, board, or backend doctor from
   passing;
2. state integrity and safety doctors;
3. runtime and assignment reliability;
4. orchestrator and backend observability;
5. knowledge and backlog update quality;
6. docs and release evidence.

Do not pick frontend issues in this section. If an issue mixes frontend and
backend work, split it: this section lands the data/artifact contract, and the
frontend section consumes it separately.

## Commit and Push Rule

Each coherent backend/core slice should end with:

```bash
python3.11 -m pytest
python3.11 -m ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
scripts/verify_v1.sh
git status --short
git add <changed-files>
git commit -m "<type>: <summary>"
git push
```

For docs-only changes, at minimum run:

```bash
git diff --check
git status --short
```

## Multica Coordination

Multica remains the issue tracker and coordination surface. For each completed
slice:

- comment in Chinese with changed files, commands run, and result;
- mark the corresponding issue done only after local verification;
- leave blocked issues with exact evidence, not generic failure text.

Multica is not responsible for merging code by itself. Codex performs final
integration, verification, commit, and push for this section.

## Current Section Prompt

Use this as the goal prompt for a Codex section dedicated to non-frontend work:

```text
You are Codex working on Ariadne's core/backend/runtime section.

Do not modify the frontend lane or append to the shared v1.0 sprint plan.
Follow docs/ops/CODEX_CORE_SECTION_EXECUTION_PLAN.md.

Your ownership is every non-frontend part of Ariadne:
domain models, store invariants, ticket lifecycle, assignment queue, daemon,
runtime locking, backends, orchestrator, planner, memory, review, board data,
CLI, safety doctors, tests, and release verification.

Keep Ariadne local-first and ticket-centered. Goal can be input metadata, but
Ticket is the center object. Align with Multica's issue-agent-runtime-board
work-management model without copying Multica's hosted server architecture.

Work in small vertical slices. For each slice, implement code, tests, docs if
needed, run verification, commit, push, and write Chinese Multica progress.

Do not touch frontend issues unless extracting a backend data contract needed
by the frontend section.
```
