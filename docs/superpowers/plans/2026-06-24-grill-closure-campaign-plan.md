# Ariadne Grill Closure Campaign Plan

> **For agentic workers:** This plan supersedes treating Phase 8 as the active
> execution boundary. Phase 8 knowledge work remains part of the product, but
> the current priority is closing the grill findings into a real browser
> product loop. Execute one phase at a time. Do not implement this whole plan in
> one branch.

## Metadata

- **Timestamp:** `2026-06-24 00:00:00 CST`
- **Source review:** `docs/reviews/grill-workflows/results/2026-06-24-final-41-grill-list.md`
- **Goal:** Turn the 41 grill findings into mergeable product-closure work.
- **Recommended branch prefix:** `codex/grill-closure-`
- **Primary user promise:** An AI Builder can use the browser Workbench to turn
  project goals and external inputs into target-project work executed by
  Codex/Claude, with evidence returned to the Workbench.

## Required Reading

Read in this order before implementing any phase:

```text
AGENTS.md
README.md
docs/adr/ADR-0004-ticket-centered-agent-workbench.md
docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md
docs/superpowers/plans/2026-06-22-multica-grade-workbench-execution-brief.md
docs/reviews/grill-workflows/results/2026-06-24-final-41-grill-list.md
```

For Multica reference, read only the files needed by the current phase:

```text
/Users/martinlos/code/multica/packages/views/issues/components/issue-detail.tsx
/Users/martinlos/code/multica/packages/views/issues/components/board-view.tsx
/Users/martinlos/code/multica/packages/views/agents/components/agents-page.tsx
/Users/martinlos/code/multica/packages/views/runtimes/components/runtimes-page.tsx
/Users/martinlos/code/multica/server/internal/handler/task_lifecycle.go
/Users/martinlos/code/multica/server/migrations/055_task_lease_and_retry.up.sql
/Users/martinlos/code/multica/server/cmd/multica/cmd_daemon.go
```

If the Multica checkout is unavailable, use the mechanism notes already
captured in `2026-06-22-multica-grade-agent-team-workbench-rebuild-plan.md`.
Do not block the work.

## Scope

Build a coherent product closure path:

```text
Sources
  -> Current Issue Delta
  -> Current Issue Set
  -> Assignment
  -> Runtime Run
  -> Evidence
  -> Review / Memory / Next Issues
  -> Version Progress
```

This plan is not a UI polish pass. It is a product-state and evidence closure
campaign.

## Non-Scope

- Do not add independent Issue persistence. Issue remains a BuildTicket
  projection.
- Do not introduce Go, Postgres, auth, hosted workspace, billing, or a Multica
  fork.
- Do not use fake-codex, demo full, static snapshots, mock data, or CLI-only
  runs as product acceptance evidence.
- Do not expose raw ProjectKnowledge CRUD as public HTTP API. Workbench may
  display provenance and derived evidence through existing product projections.
- Do not implement Query / Lint / Memory as new Phase 8 features unless a later
  approved plan explicitly does so.
- Do not start with board mutation, sidebar polish, drag/drop, or visual
  redesign before the state/evidence truth layer is fixed.

## Core Architecture

The campaign introduces a stricter product-state spine, still backed by existing
Ariadne objects:

```text
BuildTicket
  -> TicketAssignment
  -> AgentRun / ExecutionResult
  -> ReviewReport
  -> Memory / NextTickets
  -> CurrentVersionDelivery projection
```

The important change is not a new persistence model. It is a set of shared
reducers/projections so every page tells the same truth.

```text
Raw persisted state
  tickets / assignments / daemon / runs / artifacts / reviews / memory
        |
        v
Shared reducers
  current_issue_set
  current_work_snapshot
  terminal_verdict
  evidence_validity
  issue_delta_provenance
        |
        v
Workbench projections
  Context Strip / Issues / Issue Detail / Runs / Team / Inbox / Sources / Plan Changes
```

## Phase 1: Truth Layer

### Goal

Fix the product's most damaging lie: a blocked or stale run must never appear as
ready, done, succeeded, or useful execution evidence.

### Grill Issues Covered

`G-003`, `G-004`, `G-005`, `G-015`, `G-016`, `G-017`, `G-037`.

### Product Outcome

- Current Version Context, Issues, Runs, Inbox, and Issue Detail agree on the
  same active/blocked/done state.
- Stale daemon heartbeat cannot define active work.
- Blocked execution dominates optimistic stage-level success.
- Dirty pre-existing target repo state is separated from per-run output.

### Expected Code Areas

```text
ariadne_ltb/application/workbench_task_snapshot.py
ariadne_ltb/application/workbench_projection.py
ariadne_ltb/application/workbench_issues.py
ariadne_ltb/application/workbench_runtimes.py
ariadne_ltb/application/project_version_delivery.py
ariadne_ltb/application/current_version_scope.py
ariadne_ltb/execution.py or backend result capture modules
frontend/ariadne-workbench/src/widgets/current-version-context
frontend/ariadne-workbench/src/pages/issues
frontend/ariadne-workbench/src/pages/runs
```

### Implementation Requirements

- Add or centralize a terminal verdict reducer:
  - `blocked_before_execution`
  - `executed_failed`
  - `review_blocked`
  - `succeeded`
  - `unknown`
- Make projections use the reducer instead of local status guesses.
- Ignore stale daemon heartbeat for active work when assignment lifecycle is
  terminal or absent.
- Separate preflight dirty files from per-run changed files in projections.
- Mark stage successes as subordinate when the terminal verdict is blocked.

### Verification

```bash
python3.11 -m pytest
ruff check .
cd frontend/ariadne-workbench && npm run build
python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8766
```

Browser checks:

- Open `#issues`, `#issues/<blocked-key>`, `#runs`, `#inbox`.
- Verify one blocked run is blocked everywhere.
- Verify no page shows blocked execution as `succeeded`.
- Verify dirty-before-run files are not presented as agent-produced changes.

Evidence artifact:

```text
docs/evidence/grill-closure/phase1-truth-layer/
```

### Exit Criteria

This phase is mergeable when a known blocked run renders as blocked across all
Workbench surfaces, and tests/build pass.

## Phase 2: Runtime Control And Recovery

### Goal

Make the lower layer feel like a real Multica-style work-management runtime:
the user knows which assignment will run, which attempt failed, and which
actions are legal.

### Grill Issues Covered

`G-006`, `G-008`, `G-009`, `G-010`, `G-011`, `G-012`, `G-013`, `G-027`,
`G-028`, `G-029`, `G-030`.

### Product Outcome

- One issue/backend has one current runnable attempt or explicit attempt
  lineage.
- Rerun targets a specific failed assignment.
- Browser refresh does not lose recovery ability.
- One failure produces one blocker, one Inbox item, and backend-approved
  actions.
- Daemon start has an explicit scope or clearly warns about broad claiming.

### Expected Code Areas

```text
ariadne_ltb/models.py
ariadne_ltb/daemon.py
ariadne_ltb/application/assign_ticket.py
ariadne_ltb/application/run_assignment.py
ariadne_ltb/application/daemon_control.py
ariadne_ltb/application/workbench_inbox.py
ariadne_ltb/application/workbench_runtimes.py
ariadne_ltb/inbox.py
frontend/ariadne-workbench/src/pages/issues
frontend/ariadne-workbench/src/pages/runs
frontend/ariadne-workbench/src/pages/inbox
```

### Implementation Requirements

- Enforce duplicate runnable assignment rules or show explicit parent/attempt
  lineage.
- Add row-level retry actions keyed by assignment id.
- Persist or project execution gate state so recovery survives refresh.
- Add canonical blocker identity and de-duplication.
- Include backend-approved `allowed_actions` in Inbox DTOs.
- Make invalid/rejected actions durable as rejected/no-op evidence or produce no
  misleading event.
- Add daemon claim scope to start/run controls.

### Verification

- Create multiple assignments for one ticket/backend.
- Retry a specific failed assignment row.
- Refresh browser and recover the blocked issue.
- Trigger one external execution gate blocker; Inbox shows one item with only
  allowed actions.
- Start daemon from selected issue; only scoped assignment is claimable.

Evidence artifact:

```text
docs/evidence/grill-closure/phase2-runtime-control/
```

### Exit Criteria

This phase is mergeable when assignment/run/retry/recovery is deterministic and
visible without relying on browser memory.

## Phase 3: Issue Detail And Evidence Center

### Goal

Turn Issue Detail into the single fact center for a BuildTicket.

### Grill Issues Covered

`G-007`, `G-014`, `G-022`, `G-023`, `G-034`, `G-038`.

### Product Outcome

- Issue Detail has one execution log spine.
- Active and past attempts are grouped and labeled.
- Source grounding, acceptance criteria, affected modules, handoff, route,
  artifacts, diff/tests/review, memory, and next issue evidence are visible in
  one place.
- Every evidence reference can be opened or is explicitly marked invalid.

### Expected Code Areas

```text
ariadne_ltb/application/workbench_issues.py
ariadne_ltb/application/workbench_artifacts.py or new projection helper
ariadne_ltb/handoff.py
ariadne_ltb/artifacts.py
frontend/ariadne-workbench/src/pages/issues/IssueDetail.tsx
frontend/ariadne-workbench/src/shared/api/types.ts
frontend/ariadne-workbench/src/app/routes.ts
```

### Implementation Requirements

- Add categorized evidence projection:
  - source evidence;
  - handoff evidence;
  - execution artifacts;
  - review artifacts;
  - memory artifacts;
  - next-ticket artifacts.
- Add semantic artifact validity:
  - missing;
  - empty;
  - not run;
  - stale;
  - dirty before run;
  - produced by run.
- Render readable source excerpts in handoff packets.
- Add artifact/evidence viewer route or equivalent readable local action.

### Verification

- Open an issue detail page with source refs and blocked execution evidence.
- Click source evidence, handoff, execution log, diff, tests, review, memory,
  and next-ticket refs.
- Verify every visible evidence item opens or explains why it is invalid.

Evidence artifact:

```text
docs/evidence/grill-closure/phase3-evidence-center/
```

### Exit Criteria

This phase is mergeable when a reviewer can understand one ticket from Issue
Detail alone.

## Phase 4: Knowledge-To-Issue Closure

### Goal

Make the upper Ariadne layer do real work: sources, project purpose, codebase
state, and feedback must produce auditable issue deltas and handoffs.

### Grill Issues Covered

`G-002`, `G-018`, `G-019`, `G-020`, `G-021`, `G-024`, `G-025`, `G-026`,
`G-033`, `G-035`, `G-036`, `G-039`.

### Product Outcome

- Plan Changes separates current mainline source delta, repair suggestions,
  feedback previews, rejected/deferred changes, and history.
- Issue delta records compiler provenance:
  - ProjectKnowledge graph;
  - deterministic theme fallback;
  - old compiler fallback;
  - error/fallback reason.
- Target codebase snapshot is a first-class input for target-project issue
  generation.
- Source artifacts reject or mark raw HTML / low-quality extraction.
- GitHub repo understanding includes architecture/test/safety insight, not only
  inventory.
- Source lane explains queued/analyzing/blocked/analyzed/ignored/stale state.

### Expected Code Areas

```text
ariadne_ltb/application/issue_factory.py
ariadne_ltb/application/source_analysis.py
ariadne_ltb/application/repository_scanner.py
ariadne_ltb/application/build_context.py
ariadne_ltb/knowledge
ariadne_ltb/storage or .ariadne projection helpers
frontend/ariadne-workbench/src/pages/sources
frontend/ariadne-workbench/src/pages/plan-changes
```

### Implementation Requirements

- Add provenance fields to backlog preview / issue delta metadata.
- Do not expose raw ProjectKnowledge CRUD API; expose derived provenance and
  evidence through existing product projections.
- Require or explicitly downgrade missing target codebase snapshots.
- Add source artifact quality status and extraction limitations.
- Add claim-level evidence for non-trivial sources.
- Separate synthetic/internal sources from user-provided external inputs in the
  UI.

### Verification

- Add a GitHub repo source and a blog/source URL.
- Analyze sources.
- Generate Issue Delta.
- Verify each proposed issue has:
  - source claim;
  - locator/confidence;
  - affected module rationale;
  - acceptance criteria rationale;
  - compiler provenance;
  - target codebase snapshot status.

Evidence artifact:

```text
docs/evidence/grill-closure/phase4-knowledge-to-issue/
```

### Exit Criteria

This phase is mergeable when a user can explain why each generated issue exists
without opening raw `.ariadne` files.

## Phase 5: Browser Dogfood Closure Ledger

### Goal

Prove the real product loop from the browser. This phase does not excuse earlier
failures; it is the final acceptance harness that prevents future fake closure.

### Grill Issues Covered

`G-001`, `G-031`, `G-032`, `G-040`, `G-041`, plus all P0 regressions.

### Product Outcome

Workbench produces a dogfood closure ledger:

```text
target project
source ids
selected issue delta
applied current issue set
assignment/run ids
backend used
target repo diff
test command/result
review report
memory record
next issue
target version progress
```

### Expected Code Areas

```text
scripts/verify_dogfood_browser.sh
ariadne_ltb/application/project_version_delivery.py
ariadne_ltb/application/workbench_projection.py
frontend/ariadne-workbench/src/widgets/current-version-context
frontend/ariadne-workbench/src/pages/issues
frontend/ariadne-workbench/src/pages/runs
docs/dogfood
docs/evidence
```

### Implementation Requirements

- Closure ledger status values:
  - `REAL_CLOSED`;
  - `BLOCKED_WITH_EVIDENCE`;
  - `INCOMPLETE`;
  - `INVALID_EVIDENCE`.
- `REAL_CLOSED` requires real target repo diff, tests, review, memory, next issue,
  and target version progress.
- Dry-run, fake-codex, demo full, CLI-only run, or static fixture can never set
  `REAL_CLOSED`.
- Workbench must show the closure ledger or the exact blocking object.
- Product runtime list must not let dry-run/fallback masquerade as product
  execution.
- Visible shell commands that do not work must be removed or clearly disabled.

### Verification

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 scripts/verify_dogfood_browser.sh --real
```

Browser checks:

- Create/confirm target project.
- Add source.
- Generate and apply issue delta.
- Assign issue to Codex or Claude.
- Let daemon run scoped assignment.
- Verify target repo diff/tests/review/memory/next issue returns to Workbench.
- Verify closure ledger status.

Evidence artifact:

```text
docs/evidence/grill-closure/phase5-browser-dogfood/
.ariadne/dogfood/<run-id>/closure-result.json
```

### Exit Criteria

This phase is mergeable only if it either:

- produces `REAL_CLOSED`; or
- produces `BLOCKED_WITH_EVIDENCE` with exact blocker, issue detail evidence,
  Inbox item, and recovery action.

It must not claim closure on blocked-only evidence.

## Implementation Rules

- Each phase must be a separate branch and independently mergeable.
- Each phase must update evidence under `docs/evidence/grill-closure/<phase>/`.
- Each phase must include focused tests for its reducer/projection/action
  behavior.
- Frontend-affecting phases must run `npm run build`.
- Browser verification is mandatory for every phase.
- Use subagents for review before merge when a phase touches more than 8 files
  or more than 3 data projections.

## Standard Verification Commands

Use the relevant subset for each phase:

```bash
python3.11 -m pytest
ruff check .
cd frontend/ariadne-workbench && npm run build
python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8766
```

When real execution is part of the phase:

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 scripts/verify_dogfood_browser.sh --real
```

If real execution is blocked by environment, the phase may finish only as
`BLOCKED_WITH_EVIDENCE`, with exact blocker and recovery path.

## Rollback

Rollback per phase by reverting the phase commit/PR. Avoid irreversible data
migrations. If a phase adds fields to `.ariadne` JSON/JSONL records, readers
must treat absent fields as unknown/default and remain backward compatible.

## First Phase Recommendation

Start with Phase 1: Truth Layer.

Reason:

```text
If blocked execution can still display as success, every later source,
runtime, handoff, and dogfood result is untrustworthy.
```

Do not begin with UI redesign, source quality, board mutation, or sidebar polish.
Those improvements are downstream of having one truthful current-version state.
