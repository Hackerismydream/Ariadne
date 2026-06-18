# Codex-Led Ariadne Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Switch Ariadne development from Multica-driven code execution to Codex-led implementation, while keeping Multica as the external campaign board, evidence log, and read-only review/planning assistant layer.

**Architecture:** Ariadne remains a Python, local-first, ticket-centered Agent Workbench. Multica is an external development-campaign console only; it must not become Ariadne's product runtime, queue, persistence layer, backlog source of truth, or required dependency. Codex owns implementation, local verification, commit, push, and integration decisions.

**Tech Stack:** Python 3.11+, Pydantic v2, Typer, Pytest, Ruff, JSON/JSONL persistence, Git branches/worktrees.

**Campaign Tooling, outside `ariadne_ltb`:** local Multica CLI may be used for issue metadata/comments only.

---

## Decision

Use Codex as the primary implementation agent.

The current Multica-driven mode is too slow because it adds queue, resource
binding, run inspection, review, verifier, and landing steps before Ariadne's
own product work advances. Multica remains useful, but only as:

- an external campaign issue board;
- a campaign metadata registry, not Ariadne's local product backlog;
- a record of decisions, evidence, and landing notes;
- a place to run read-only review, planning, or documentation agents;
- a reference implementation for issue/agent/runtime maturity.

It should not be used as the normal code-writing engine for Ariadne until
Multica-side resource isolation, worktree binding, reviewer automation, and
landing gates are proven reliable.

Product Core batch work should not wait on Multica comments. The hard gates for
Codex-led code batches are:

```text
local tests pass
ruff passes
CLI smoke commands pass
scripts/verify_v1.sh passes
no P0 reviewer finding remains unresolved
branch is pushed
```

Multica campaign evidence can be synced after local verification. It is not the
source of product truth.

## Current Evidence

- Branch before this plan was created: `codex/ari-mul-96-merge-gate-policy-engine`.
- Plan branch: `codex/ariadne-codex-led-delivery-plan`.
- Multica issue counts observed on 2026-06-17:
  - `backlog`: 90
  - `in_review`: 3
  - `done`: 7
- Current active code issue:
  - LOC-102 / ARI-MUL-97: conflict detection and conflict report.
  - Implementation run completed in isolated worktree.
  - Work remained in review/landing state after implementation had already passed local verification.
- Efficiency baseline:
  - The old mode made one implemented issue wait on diff collection, resource-binding checks, reviewer dispatch, verifier dispatch, landing reports, and controller updates.
  - This plan removes those steps from the normal product-code critical path.
- Current authoritative Ariadne direction:
  - `docs/adr/ADR-0004-ticket-centered-agent-workbench.md`
  - `docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md`
  - `docs/capability_surface/ARIADNE_CAPABILITY_SURFACE.md`

## Non-Scope

- Do not copy Multica's Go server, Postgres schema, WebSocket runtime, auth,
  multi-tenant workspace model, or hosted frontend architecture into Ariadne.
- Do not make Multica a dependency of `ariadne_ltb`.
- Do not implement default auto-commit, auto-push, auto-merge, or PR creation
  inside Ariadne runtime backends.
- Do not continue the full landing-pipeline issue train before product-core
  work resumes.
- Do not delete the 100+ Multica issues. Reclassify and batch them.
- Do not let Multica campaign status decide whether Ariadne product work is
  complete.

## Operating Model

```text
Human owner
  -> product direction and final main-merge judgment

Codex
  -> implementation lead
  -> local reviewer / verifier / integrator
  -> commit and push after checks pass
  -> writes Chinese campaign evidence to Multica when useful

Multica
  -> external campaign issue board
  -> campaign metadata registry
  -> evidence log
  -> read-only review / planning / docs assistant surface

Multica agents
  -> review diffs against a fixed commit SHA
  -> verify acceptance checklists in read-only mode
  -> refine issue descriptions
  -> review docs and architecture
  -> do not mutate Ariadne product code in the normal campaign
```

Exception rule:

```text
A Multica agent may change Ariadne product code only for an explicitly assigned
one-off repair, in an isolated worktree, with verified work_dir, allowed paths,
and Codex final review before commit/push.
```

## Subagent Review Summary

Three subagents reviewed the first draft of this plan.

Architecture review:

- The direction is compatible with ADR-0004.
- Required correction: Multica CLI must not be listed as product tech stack.
- Required correction: Multica campaign status must not be treated as product
  completion.

Execution-throughput review:

- The direction improves throughput only if Multica comments do not become a
  synchronous gate.
- Product Core Batch 1 was too large and needed to split into 1A and 1B.
- Read-only Multica lanes need a non-blocking output contract.

Risk/test/rollback review:

- Phase chaining must be explicit: each product batch starts only after the
  previous branch is merged or intentionally stacked.
- LOC-102 review must cover all changed files, not only new files.
- Commit commands must avoid broad `git add docs`.
- Each claimed LOC must have matching tests and acceptance criteria.

This revised plan incorporates those review findings.

## Issue Reclassification

Reclassify existing Multica issues into these lanes:

| Lane | Meaning | Execution owner | Action |
| --- | --- | --- | --- |
| `product_core` | Ariadne's differentiating ticket/backlog update loop | Codex | Implement first |
| `runtime_maturity` | Assignment, daemon, retry, events, capability, safety | Codex | Implement after product core starts |
| `workbench_local` | Static board, read-only local adapter, local UX visibility | Codex | Implement after data model stabilizes |
| `dogfood_release` | Onboarding, release evidence, dogfood pack | Codex | Implement near v1.0 release |
| `dev_infra_deferred` | Work that only improves Multica-driven development | Deferred | Pause unless it blocks Codex-led delivery |
| `readonly_support` | Review, planning, docs, issue hygiene | Multica agents | Safe parallel lane |

## Concrete Issue Decisions

### Finish

- LOC-102 / ARI-MUL-97: Conflict detection and conflict report.

### Conditional

- LOC-103 / ARI-MUL-98: Branch freshness and safe update gate.

Run LOC-103 only if LOC-102 review proves branch freshness is actually blocking
Codex-led branch landing. Otherwise defer it with LOC-104 through LOC-107.

### Defer

These are useful later but should not block Ariadne product work now:

- LOC-104 / ARI-MUL-99: Gated auto-commit and auto-push.
- LOC-105 / ARI-MUL-100: Optional gated auto-merge.
- LOC-106 / ARI-MUL-101: Multica landing status sync.
- LOC-107 / ARI-MUL-102: Worktree cleanup and rollback policy.

### Product Core Batch 1A

- LOC-31 / ARI-MUL-26: Ticket relationship graph and dependency invariants.
- LOC-32 / ARI-MUL-27: Lifecycle transition gates.
- LOC-37 / ARI-MUL-32: Dependency-aware ticket promotion.

### Product Core Batch 1B

- LOC-34 / ARI-MUL-29: Idempotent backlog preview/apply.
- LOC-35 / ARI-MUL-30: Split backlog feedback generators.
- LOC-36 / ARI-MUL-31: Backlog conflict resolver.

### Runtime-Maturity Batch 2

- LOC-38 / ARI-MUL-33: Retry/backoff/dead-letter failure policy.
- LOC-39 / ARI-MUL-34: Cancel, pause, resume, and supersede running work.
- LOC-40 / ARI-MUL-35: Unified audit event log and replay fixtures.
- LOC-48 / ARI-MUL-43: Local daemon capacity hints and assignment queue.
- LOC-61 / ARI-MUL-56: Agent role capability contracts.

### Workbench Batch 3A

- LOC-62 / ARI-MUL-57: Static board semantic parity with CLI state.
- LOC-67 / ARI-MUL-62: Local web data adapter.
- LOC-81 / ARI-MUL-76: Run progress timeline.

### Workbench Batch 3B

These remain planned, but do not block Product Core or Runtime Maturity:

- LOC-66 / ARI-MUL-61: Local web workbench architecture ADR.
- LOC-70 / ARI-MUL-65: Web app shell and navigation.
- LOC-71 / ARI-MUL-66: Ticket board swimlanes.
- LOC-72 / ARI-MUL-67: Ticket detail page.

### Dogfood/Release Batch 4

- LOC-51 / ARI-MUL-46: Local onboarding and doctor golden path.
- LOC-53 / ARI-MUL-48: Release evidence packet.
- LOC-64 / ARI-MUL-59: End-to-end dogfood scenario pack.
- LOC-65 / ARI-MUL-60: Issue metadata governance and lint.

## Global Preflight For Every Implementation Phase

- [ ] **Step 1: Confirm branch and workspace**

Run:

```bash
pwd
git rev-parse --show-toplevel
git status --short --branch
git fetch origin
```

Expected:

- `pwd` is `/Users/martinlos/code/Ariadne` or the intended isolated worktree.
- `git status --short --branch` has no unrelated dirty files.
- If a plan document is uncommitted, commit/push it before switching branches.

- [ ] **Step 2: Confirm mainline base**

For non-stacked branches, run:

```bash
git switch main
git pull --ff-only origin main
git status --short --branch
```

Expected:

- Local `main` is up to date.
- Worktree is clean.

Stacked branch exception:

```text
Only stack if the previous branch is intentionally not merged yet and this is
written in the branch description or Multica campaign note. A stacked branch
must state its base branch and cannot be merged before its base branch.
```

- [ ] **Step 3: Record local evidence fallback path**

For each batch, create a local evidence note:

```bash
mkdir -p docs/development_evidence
```

Use a file name:

```text
docs/development_evidence/<branch-name>.md
```

Expected:

- If Multica is down, evidence is still recorded locally.
- The evidence note can be synced to Multica later.

## Phase 1: Finish LOC-102 And Stop The Old Train

**Files:**
- Modify: Multica LOC-102 comments/metadata through CLI if Multica is available.
- Modify: Multica LOC-108 comments/metadata through CLI if Multica is available.
- No Ariadne product code changes unless LOC-102 review finds a blocker.

- [ ] **Step 1: Inspect LOC-102 worktree state**

Run:

```bash
git -C /Users/martinlos/code/Ariadne.worktrees/ari-mul-97-conflict-detection-report status --short --branch
git -C /Users/martinlos/code/Ariadne.worktrees/ari-mul-97-conflict-detection-report diff --stat
git -C /Users/martinlos/code/Ariadne.worktrees/ari-mul-97-conflict-detection-report ls-files --others --exclude-standard
```

Expected:

- Branch is `codex/ari-mul-97-conflict-detection-report`.
- Changed files are intentional.
- Untracked files are either staged with `git add -N` for review or removed
  before final verification.

- [ ] **Step 2: Create a complete LOC-102 diff view**

Run:

```bash
cd /Users/martinlos/code/Ariadne.worktrees/ari-mul-97-conflict-detection-report
git ls-files --others --exclude-standard | xargs -r git add -N
git status --short --branch
git diff --stat
git diff --binary | shasum -a 256
```

Expected:

- All changed and untracked files are represented in `git diff`.
- One SHA-256 hash is printed for optional campaign evidence.

- [ ] **Step 3: Run LOC-102 verification locally**

Run:

```bash
cd /Users/martinlos/code/Ariadne.worktrees/ari-mul-97-conflict-detection-report
python3.11 -m pytest
python3.11 -m ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
scripts/verify_v1.sh
git status --short --branch
```

Expected:

- All commands pass.
- Only intentional source/test changes remain.
- Generated `.ariadne/` state is ignored by git.

- [ ] **Step 4: Review all LOC-102 changed files before committing**

Run:

```bash
cd /Users/martinlos/code/Ariadne.worktrees/ari-mul-97-conflict-detection-report
git diff -- ariadne_ltb/board.py ariadne_ltb/conflicts.py ariadne_ltb/landing_gate.py ariadne_ltb/models.py ariadne_ltb/orchestrator.py tests/test_conflicts.py tests/test_landing_gate.py
```

Pass criteria:

- No Multica-specific issue IDs are hardcoded into product runtime modules.
- Missing or unsafe landing policy fails closed.
- Conflict report is generic local Git safety behavior.
- Board additions remain product-visible and not campaign-only.
- Tests cover blocked and passing cases.

- [ ] **Step 5: Commit and push LOC-102 if verification passes**

Run:

```bash
cd /Users/martinlos/code/Ariadne.worktrees/ari-mul-97-conflict-detection-report
git add ariadne_ltb/board.py ariadne_ltb/conflicts.py ariadne_ltb/landing_gate.py ariadne_ltb/models.py ariadne_ltb/orchestrator.py tests/test_conflicts.py tests/test_landing_gate.py
git commit -m "feat: add conflict detection report"
git push -u origin codex/ari-mul-97-conflict-detection-report
```

Expected:

- Branch push succeeds.
- Do not merge to `main` in this step.

- [ ] **Step 6: Write one Chinese closeout note**

If Multica is available, write one LOC-102 closeout comment with:

```text
状态：已提交并推送分支
分支：
commit：
验证：
风险：
下一步：
```

If Multica is unavailable, write the same note to:

```text
docs/development_evidence/codex-ari-mul-97-conflict-detection-report.md
```

Expected:

- Campaign evidence exists either in Multica or in local docs.
- Product progress is not blocked by Multica availability.

- [ ] **Step 7: Write one Chinese LOC-108 strategy update**

If Multica is available, write:

```text
状态：策略已切换
做了什么：Ariadne 开发主线切换为 Codex-led。Multica 继续作为 issue board、证据记录和只读 review/planning 辅助。
验证：后续代码 batch 以本地测试、ruff、CLI smoke、scripts/verify_v1.sh 和 pushed branch 为硬 gate。
风险：LOC-104 到 LOC-107 暂缓，除非直接阻塞 Codex-led product batch。
下一步：Codex 直接推进 Product Core Batch 1A。
```

If Multica is unavailable, write this update to:

```text
docs/development_evidence/codex-led-strategy-update.md
```

Expected: future readers do not continue the old Multica-driven landing train.

## Phase 2: Route Cleanup And Product Boundary Repair

**Files:**
- Modify: `docs/ops/OVERNIGHT_MULTICA_SUPERVISION_PROTOCOL.md`
- Modify: `docs/development_report.md`
- Conditionally modify: `ariadne_ltb/landing_gate.py`
- Conditionally modify: `ariadne_ltb/conflicts.py`
- Conditionally modify: `ariadne_ltb/orchestrator.py`
- Conditionally modify: `tests/test_landing_gate.py`
- Conditionally modify: `tests/test_conflicts.py`

This phase is docs-first. Product code changes happen only if the audit finds
campaign-specific coupling in `ariadne_ltb`.

- [ ] **Step 1: Create cleanup branch**

Run:

```bash
git switch main
git pull --ff-only origin main
git switch -c codex/ariadne-codex-led-route-cleanup
git status --short --branch
```

Expected: clean branch from current `main`.

- [ ] **Step 2: Add Codex-led mode to the supervision protocol**

Modify `docs/ops/OVERNIGHT_MULTICA_SUPERVISION_PROTOCOL.md`.

Add after `Architecture Boundary`:

```markdown
## Current Campaign Mode

The current Ariadne v1.0 campaign uses Codex-led implementation.

Codex writes code, runs local verification, commits, pushes, and integrates.
Multica remains the external campaign board and evidence log. Multica agents
may review, verify, plan, or document in read-only mode, but they are not the
default code-writing layer.

The earlier Multica-driven overnight mode is paused because local resource
binding, worktree isolation, review dispatch, verifier dispatch, and landing
automation cost more time than they saved.
```

Expected: future readers see the new execution mode before the older overnight
loop.

- [ ] **Step 3: Add explicit pause list**

Modify the same document.

Add:

```markdown
## Paused Development-Infrastructure Issues

The following Multica issues are deferred unless they directly block Codex-led
delivery:

- LOC-104 / ARI-MUL-99: Gated auto-commit and auto-push.
- LOC-105 / ARI-MUL-100: Optional gated auto-merge.
- LOC-106 / ARI-MUL-101: Multica landing status sync.
- LOC-107 / ARI-MUL-102: Worktree cleanup and rollback policy.

They are not product-core issues. They improve a Multica-driven development
campaign and should not delay Ariadne ticket/backlog/runtime maturity.
```

Expected: old infrastructure queue is visibly deprioritized.

- [ ] **Step 4: Audit product code for Multica campaign coupling**

Run:

```bash
rg -n "Multica|multica|LOC-|ARI-MUL|overnight|controller|landing_sync|autopush|auto-merge|resource_binding" ariadne_ltb tests docs/ops
```

Expected:

- `docs/ops` may contain campaign-specific terms.
- `ariadne_ltb` should not require Multica-specific terms.
- Any product-code hit must be either generic documentation text or removed.

- [ ] **Step 5: Repair campaign coupling only if found**

If `ariadne_ltb/*.py` contains campaign-only logic:

- Move external campaign sync code to `scripts/multica_campaign_sync.py`.
- Keep product-safe logic in `ariadne_ltb`.
- Do not import `scripts/multica_campaign_sync.py` from `ariadne_ltb`.

Verification:

```bash
rg -n "LOC-|ARI-MUL|overnight|resource_binding" ariadne_ltb || true
```

Expected: no product-runtime dependency on campaign identifiers.

- [ ] **Step 6: Update development report**

Modify `docs/development_report.md` with:

```markdown
## Codex-led delivery mode

Ariadne development now uses Codex as the primary implementation agent.
Multica is retained as the external campaign board, evidence log, and read-only
assistant surface. This avoids spending the v1.0 budget on development
infrastructure automation before Ariadne's own ticket/backlog/runtime maturity
is complete.
```

Expected: development report records the route change.

- [ ] **Step 7: Verify cleanup branch**

Run:

```bash
python3.11 -m pytest
python3.11 -m ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
scripts/verify_v1.sh
git status --short --branch
```

Expected: all commands pass; only intended docs or conditional product-boundary
repair files are dirty.

- [ ] **Step 8: Commit and push cleanup branch**

Run:

```bash
git add docs/ops/OVERNIGHT_MULTICA_SUPERVISION_PROTOCOL.md docs/development_report.md
git add -u ariadne_ltb tests scripts
git commit -m "docs: switch Ariadne campaign to Codex-led delivery"
git push -u origin codex/ariadne-codex-led-route-cleanup
```

Expected: pushed branch contains only route cleanup and conditional
product-boundary repair.

## Phase 3A: Product Core Batch 1A

**Files:**
- Modify: `ariadne_ltb/models.py`
- Modify: `ariadne_ltb/storage.py`
- Modify: `ariadne_ltb/cli.py`
- Create or modify: `ariadne_ltb/ticket_graph.py`
- Create or modify: `ariadne_ltb/lifecycle.py`
- Test: `tests/test_ticket_graph.py`
- Test: `tests/test_ticket_lifecycle.py`

This branch covers LOC-31, LOC-32, and LOC-37 only.

- [ ] **Step 1: Create product-core 1A branch**

Run after Phase 2 is merged to `main`, or explicitly stack on the Phase 2 branch:

```bash
git switch main
git pull --ff-only origin main
git switch -c codex/ariadne-product-core-1a-ticket-state
```

Expected: clean branch from current `main`.

- [ ] **Step 2: Add ticket relationship tests**

Create `tests/test_ticket_graph.py` with tests for:

- parent/child ticket relationship serialization;
- duplicate relationship rejection;
- cycle rejection;
- blocked-by dependency state;
- dependency-aware promotion blocks a ticket when blockers are not done.

Run:

```bash
python3.11 -m pytest tests/test_ticket_graph.py -q
```

Expected before implementation: fails because graph helpers are missing.

- [ ] **Step 3: Implement ticket relationship graph**

Create or modify `ariadne_ltb/ticket_graph.py`.

Required functions:

```python
def add_relationship(store, source_ticket_id: str, target_ticket_id: str, relation: str) -> None: ...
def validate_no_cycle(store, source_ticket_id: str, target_ticket_id: str) -> None: ...
def list_blockers(store, ticket_id: str) -> list[str]: ...
def list_dependents(store, ticket_id: str) -> list[str]: ...
def can_promote_ticket(store, ticket_id: str) -> bool: ...
```

Run:

```bash
python3.11 -m pytest tests/test_ticket_graph.py -q
```

Expected: passes.

- [ ] **Step 4: Add lifecycle transition tests**

Create `tests/test_ticket_lifecycle.py` with tests for:

- `backlog -> ready`;
- `ready -> assigned`;
- `assigned -> running`;
- `running -> review`;
- `review -> done`;
- invalid transition rejection;
- blocked dependency prevents promotion;
- each rejected transition records a typed reason.

Run:

```bash
python3.11 -m pytest tests/test_ticket_lifecycle.py -q
```

Expected before implementation: fails because transition gate helpers are
missing.

- [ ] **Step 5: Implement lifecycle transition gates**

Create or modify `ariadne_ltb/lifecycle.py`.

Required functions:

```python
def validate_ticket_transition(ticket, new_status: str, blockers: list[str]) -> None: ...
def transition_ticket(store, ticket_id: str, new_status: str, reason: str) -> object: ...
```

Run:

```bash
python3.11 -m pytest tests/test_ticket_lifecycle.py tests/test_ticket_graph.py -q
```

Expected: passes.

- [ ] **Step 6: Run branch verification**

Run:

```bash
python3.11 -m pytest
python3.11 -m ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
scripts/verify_v1.sh
git status --short --branch
```

Expected: all pass; only intended files are dirty.

- [ ] **Step 7: Commit and push**

Run:

```bash
git add ariadne_ltb/models.py ariadne_ltb/storage.py ariadne_ltb/cli.py ariadne_ltb/ticket_graph.py ariadne_ltb/lifecycle.py tests/test_ticket_graph.py tests/test_ticket_lifecycle.py
git commit -m "feat: add ticket graph and lifecycle gates"
git push -u origin codex/ariadne-product-core-1a-ticket-state
```

Expected: branch is pushed. Multica campaign evidence may be synced after the
push, but it is not a hard product gate.

## Phase 3B: Product Core Batch 1B

**Files:**
- Modify: `ariadne_ltb/models.py`
- Modify: `ariadne_ltb/storage.py`
- Modify: `ariadne_ltb/cli.py`
- Modify: `ariadne_ltb/board.py`
- Create or modify: `ariadne_ltb/backlog.py`
- Test: `tests/test_backlog_update.py`

This branch covers LOC-34, LOC-35, and LOC-36 only.

- [ ] **Step 1: Create product-core 1B branch**

Run after Phase 3A is merged to `main`, or explicitly stack on the Phase 3A
branch:

```bash
git switch main
git pull --ff-only origin main
git switch -c codex/ariadne-product-core-1b-backlog-mutation
```

Expected: clean branch from current `main`.

- [ ] **Step 2: Add backlog preview/apply tests**

Create `tests/test_backlog_update.py` with tests for:

- generating a preview from new source feedback;
- splitting one feedback source into multiple candidate ticket operations;
- detecting conflicting operations against the same ticket;
- generating `add_ticket`, `update_ticket`, `defer_ticket`,
  `supersede_ticket`, and `promote_ticket` operations;
- applying the same preview twice without duplicate tickets;
- rejecting stale preview apply when source evidence changed;
- board shows preview and applied deltas.

Run:

```bash
python3.11 -m pytest tests/test_backlog_update.py -q
```

Expected before implementation: fails because backlog preview/apply does not
exist.

- [ ] **Step 3: Implement backlog preview/apply**

Create or modify `ariadne_ltb/backlog.py`.

Required data concepts:

```text
BacklogPreview
BacklogOperation
operation_type = add_ticket | update_ticket | defer_ticket | supersede_ticket | promote_ticket
source_evidence_hash
conflict_reason
applied_at
```

Required CLI:

```bash
python3.11 -m ariadne_ltb.cli backlog preview examples/sources/*.md
python3.11 -m ariadne_ltb.cli backlog apply <preview_id>
```

Run:

```bash
python3.11 -m pytest tests/test_backlog_update.py -q
```

Expected: passes.

- [ ] **Step 4: Update board for backlog mutation trace**

Modify `ariadne_ltb/board.py`.

Board must show:

```text
Source / Feedback
  -> Preview
  -> Operations
  -> Conflicts
  -> Applied Ticket Changes
  -> Related Tickets
```

Run:

```bash
python3.11 -m ariadne_ltb.cli export board
rg -n "Backlog Preview|Ticket Changes|Related Tickets|Conflicts" .ariadne/board/board.md
```

Expected: each term has a match.

- [ ] **Step 5: Run branch verification**

Run:

```bash
python3.11 -m pytest
python3.11 -m ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
scripts/verify_v1.sh
git status --short --branch
```

Expected: all pass; only intended files are dirty.

- [ ] **Step 6: Commit and push**

Run:

```bash
git add ariadne_ltb/models.py ariadne_ltb/storage.py ariadne_ltb/cli.py ariadne_ltb/board.py ariadne_ltb/backlog.py tests/test_backlog_update.py
git commit -m "feat: add backlog preview and apply"
git push -u origin codex/ariadne-product-core-1b-backlog-mutation
```

Expected: branch is pushed. Multica campaign evidence may be synced after the
push, but it is not a hard product gate.

## Phase 4: Runtime-Maturity Batch 2

**Files:**
- Modify: `ariadne_ltb/models.py`
- Modify: `ariadne_ltb/daemon.py`
- Modify: `ariadne_ltb/journal.py`
- Modify: `ariadne_ltb/cli.py`
- Create or modify: `ariadne_ltb/retry.py`
- Create or modify: `ariadne_ltb/audit.py`
- Create or modify: `ariadne_ltb/agent_capabilities.py`
- Test: `tests/test_retry_policy.py`
- Test: `tests/test_runtime_control.py`
- Test: `tests/test_audit_replay.py`
- Test: `tests/test_agent_capabilities.py`

This branch covers LOC-38, LOC-39, LOC-40, LOC-48, and LOC-61.

- [ ] **Step 1: Create runtime branch**

Run after Product Core Batch 1A is merged. Product Core Batch 1B may run before
or after this branch if there is no overlapping file conflict; do not merge two
branches into `main` at the same time.

```bash
git switch main
git pull --ff-only origin main
git switch -c codex/ariadne-runtime-maturity-batch-2
```

Expected: clean branch from current `main`.

- [ ] **Step 2: Add retry/dead-letter tests**

Create `tests/test_retry_policy.py` with tests for:

- retry count increments;
- retry stops after configured max attempts;
- dead-letter records typed failure reason;
- retry preserves original ticket and assignment references.

Run:

```bash
python3.11 -m pytest tests/test_retry_policy.py -q
```

Expected before implementation: fails.

- [ ] **Step 3: Implement retry/dead-letter policy**

Create or modify `ariadne_ltb/retry.py`.

Required functions:

```python
def should_retry(assignment, max_attempts: int) -> bool: ...
def create_retry_assignment(store, assignment_id: str, reason: str) -> object: ...
def mark_dead_letter(store, assignment_id: str, reason: str) -> object: ...
```

Run:

```bash
python3.11 -m pytest tests/test_retry_policy.py -q
```

Expected: passes.

- [ ] **Step 4: Add runtime control tests**

Create `tests/test_runtime_control.py` with tests for:

- pausing a queued assignment;
- resuming a paused assignment;
- cancelling a queued assignment;
- superseding a ticket with a replacement ticket;
- refusing to cancel a running assignment unless backend supports cancellation;
- local daemon capacity hint prevents claiming more than configured capacity.

Run:

```bash
python3.11 -m pytest tests/test_runtime_control.py -q
```

Expected before implementation: fails.

- [ ] **Step 5: Implement runtime control commands and capacity hints**

Modify `ariadne_ltb/cli.py` and `ariadne_ltb/daemon.py`.

Required CLI:

```bash
python3.11 -m ariadne_ltb.cli assignment pause <assignment_id>
python3.11 -m ariadne_ltb.cli assignment resume <assignment_id>
python3.11 -m ariadne_ltb.cli assignment cancel <assignment_id>
python3.11 -m ariadne_ltb.cli ticket supersede <ticket_id_or_key> --by <ticket_id_or_key>
python3.11 -m ariadne_ltb.cli daemon status
```

Run:

```bash
python3.11 -m pytest tests/test_runtime_control.py -q
```

Expected: passes.

- [ ] **Step 6: Add audit replay tests**

Create `tests/test_audit_replay.py` with tests for:

- event append order;
- replay reconstructs ticket status;
- replay reconstructs assignment status;
- corrupted event reports typed failure without modifying store.

Run:

```bash
python3.11 -m pytest tests/test_audit_replay.py -q
```

Expected before implementation: fails.

- [ ] **Step 7: Implement audit event log and replay fixtures**

Create or modify `ariadne_ltb/audit.py`.

Required CLI:

```bash
python3.11 -m ariadne_ltb.cli audit export
python3.11 -m ariadne_ltb.cli audit replay --dry-run
```

Run:

```bash
python3.11 -m pytest tests/test_audit_replay.py -q
```

Expected: passes.

- [ ] **Step 8: Add agent capability contract tests**

Create `tests/test_agent_capabilities.py` with tests for:

- agent role declares supported planners;
- agent role declares supported backends;
- route decision refuses incompatible backend;
- board shows capability mismatch reason.

Run:

```bash
python3.11 -m pytest tests/test_agent_capabilities.py -q
```

Expected before implementation: fails.

- [ ] **Step 9: Implement agent role capability contracts**

Create or modify `ariadne_ltb/agent_capabilities.py`.

Required functions:

```python
def load_agent_capabilities(store) -> list[object]: ...
def validate_route_capability(agent_role: str, backend: str, planner: str) -> None: ...
```

Run:

```bash
python3.11 -m pytest tests/test_agent_capabilities.py -q
```

Expected: passes.

- [ ] **Step 10: Run runtime batch verification**

Run:

```bash
python3.11 -m pytest
python3.11 -m ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
scripts/verify_v1.sh
git status --short --branch
```

Expected: all pass; only intended files are dirty.

- [ ] **Step 11: Commit and push**

Run:

```bash
git add ariadne_ltb/models.py ariadne_ltb/daemon.py ariadne_ltb/journal.py ariadne_ltb/cli.py ariadne_ltb/retry.py ariadne_ltb/audit.py ariadne_ltb/agent_capabilities.py tests/test_retry_policy.py tests/test_runtime_control.py tests/test_audit_replay.py tests/test_agent_capabilities.py
git commit -m "feat: harden runtime assignment lifecycle"
git push -u origin codex/ariadne-runtime-maturity-batch-2
```

Expected: branch is pushed.

## Phase 5A: Workbench Batch 3A

**Files:**
- Modify: `ariadne_ltb/board.py`
- Create or modify: `ariadne_ltb/web_data.py`
- Modify: `ariadne_ltb/cli.py`
- Test: `tests/test_board_semantics.py`
- Test: `tests/test_web_data_adapter.py`

This branch covers LOC-62, LOC-67, and LOC-81 only.

- [ ] **Step 1: Create workbench 3A branch**

Run after Product Core Batch 1B is merged:

```bash
git switch main
git pull --ff-only origin main
git switch -c codex/ariadne-workbench-3a-board-data
```

Expected: clean branch from current `main`.

- [ ] **Step 2: Add board semantic parity tests**

Create `tests/test_board_semantics.py` with tests that require the board to show:

- ticket status;
- relationships;
- assignment state;
- agent run timeline;
- review verdict;
- memory path;
- backlog preview/apply trace.

Run:

```bash
python3.11 -m pytest tests/test_board_semantics.py -q
```

Expected before implementation: fails.

- [ ] **Step 3: Implement board semantic parity**

Modify `ariadne_ltb/board.py`.

Run:

```bash
python3.11 -m pytest tests/test_board_semantics.py -q
python3.11 -m ariadne_ltb.cli export board
```

Expected: test passes and generated board includes required sections.

- [ ] **Step 4: Add local web data adapter tests**

Create `tests/test_web_data_adapter.py` with tests for:

- loading tickets without mutating store;
- loading board data without external services;
- refusing command execution through read-only adapter;
- stable JSON payload for ticket detail;
- run progress timeline is present in JSON output.

Run:

```bash
python3.11 -m pytest tests/test_web_data_adapter.py -q
```

Expected before implementation: fails.

- [ ] **Step 5: Implement local web data adapter**

Create or modify `ariadne_ltb/web_data.py`.

Required behavior:

```text
read-only by default
JSON serializable
no command execution
no external API calls
no writes to .ariadne
```

Run:

```bash
python3.11 -m pytest tests/test_web_data_adapter.py -q
```

Expected: passes.

- [ ] **Step 6: Run workbench verification**

Run:

```bash
python3.11 -m pytest
python3.11 -m ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
scripts/verify_v1.sh
git status --short --branch
```

Expected: all pass; only intended files are dirty.

- [ ] **Step 7: Commit and push**

Run:

```bash
git add ariadne_ltb/board.py ariadne_ltb/web_data.py ariadne_ltb/cli.py tests/test_board_semantics.py tests/test_web_data_adapter.py
git commit -m "feat: expose local board data"
git push -u origin codex/ariadne-workbench-3a-board-data
```

Expected: branch is pushed.

## Phase 5B: Workbench Batch 3B

**Files:**
- Create or modify: `docs/architecture/ARIADNE_LOCAL_WEB_WORKBENCH.md`
- Create or modify: `ariadne_ltb/board_server.py`
- Modify: `ariadne_ltb/cli.py`
- Test: `tests/test_board_server.py`

This branch covers LOC-66, LOC-70, LOC-71, and LOC-72 only if a simple local
server is still needed after Batch 3A. It must remain local, read-only by
default, and non-hosted.

- [ ] **Step 1: Create workbench 3B branch**

Run after Workbench Batch 3A is merged:

```bash
git switch main
git pull --ff-only origin main
git switch -c codex/ariadne-workbench-3b-local-server
```

Expected: clean branch from current `main`.

- [ ] **Step 2: Write local web workbench ADR**

Create or modify `docs/architecture/ARIADNE_LOCAL_WEB_WORKBENCH.md`.

Required decisions:

```text
local-only
127.0.0.1 default host
read-only JSON adapter by default
no auth system for v1.x
no hosted SaaS assumptions
static board remains supported
```

Expected: ADR explains why Ariadne is not copying Multica's hosted frontend.

- [ ] **Step 3: Add board server tests**

Create `tests/test_board_server.py` with tests for:

- server binds to `127.0.0.1` by default;
- static board files are served;
- read-only JSON endpoint is served;
- mutating commands are refused.

Run:

```bash
python3.11 -m pytest tests/test_board_server.py -q
```

Expected before implementation: fails.

- [ ] **Step 4: Implement local board server command**

Create or modify `ariadne_ltb/board_server.py` and `ariadne_ltb/cli.py`.

Required command:

```bash
python3.11 -m ariadne_ltb.cli board serve --host 127.0.0.1 --port 8765
```

Run:

```bash
python3.11 -m pytest tests/test_board_server.py -q
```

Expected: passes.

- [ ] **Step 5: Run workbench 3B verification**

Run:

```bash
python3.11 -m pytest
python3.11 -m ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
scripts/verify_v1.sh
git status --short --branch
```

Expected: all pass.

- [ ] **Step 6: Commit and push**

Run:

```bash
git add docs/architecture/ARIADNE_LOCAL_WEB_WORKBENCH.md ariadne_ltb/board_server.py ariadne_ltb/cli.py tests/test_board_server.py
git commit -m "feat: add local board server"
git push -u origin codex/ariadne-workbench-3b-local-server
```

Expected: branch is pushed.

## Phase 6: Dogfood And Release Evidence Batch 4

**Files:**
- Modify: `README.md`
- Modify: `docs/development_report.md`
- Create or modify: `docs/evaluation/v1_0_evaluation.md`
- Create or modify: `docs/demo/ARIADNE_V1_DEMO_SCRIPT.md`
- Create or modify: `docs/ops/V1_RELEASE_CHECKLIST.md`
- Create or modify: `scripts/verify_v1.sh`
- Create or modify: `ariadne_ltb/metadata_lint.py`
- Test: `tests/test_release_evidence.py`
- Test: `tests/test_metadata_lint.py`

This branch covers LOC-51, LOC-53, LOC-64, and LOC-65.

- [ ] **Step 1: Create release branch**

Run after Product Core, Runtime, and Workbench 3A are merged:

```bash
git switch main
git pull --ff-only origin main
git switch -c codex/ariadne-dogfood-release-batch-4
```

Expected: clean branch from current `main`.

- [ ] **Step 2: Add release evidence tests**

Create `tests/test_release_evidence.py` with tests for:

- release packet contains verification commands;
- release packet links board output;
- release packet links memory and next tickets;
- doctor output redacts secrets;
- demo script commands are executable locally.

Run:

```bash
python3.11 -m pytest tests/test_release_evidence.py -q
```

Expected before implementation: fails.

- [ ] **Step 3: Add metadata governance tests**

Create `tests/test_metadata_lint.py` with tests for:

- issue metadata keys use allowed prefixes;
- campaign metadata is not required by product runtime;
- secret-looking values are rejected;
- malformed ticket metadata reports file path and key.

Run:

```bash
python3.11 -m pytest tests/test_metadata_lint.py -q
```

Expected before implementation: fails.

- [ ] **Step 4: Implement release evidence and metadata lint**

Create or modify docs, scripts, and `ariadne_ltb/metadata_lint.py` so these
commands work:

```bash
scripts/verify_v1.sh
python3.11 -m ariadne_ltb.cli doctor metadata
```

Required evidence output paths:

```text
.ariadne/board/
docs/evaluation/v1_0_evaluation.md
docs/development_report.md
```

Run:

```bash
python3.11 -m pytest tests/test_release_evidence.py tests/test_metadata_lint.py -q
scripts/verify_v1.sh
```

Expected: passes.

- [ ] **Step 5: Run full release verification**

Run:

```bash
python3.11 -m pytest
python3.11 -m ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
scripts/verify_v1.sh
git status --short --branch
```

Expected: all pass.

- [ ] **Step 6: Commit and push**

Run:

```bash
git add README.md docs/development_report.md docs/evaluation/v1_0_evaluation.md docs/demo/ARIADNE_V1_DEMO_SCRIPT.md docs/ops/V1_RELEASE_CHECKLIST.md scripts/verify_v1.sh ariadne_ltb/metadata_lint.py tests/test_release_evidence.py tests/test_metadata_lint.py
git commit -m "docs: add Ariadne v1 release evidence"
git push -u origin codex/ariadne-dogfood-release-batch-4
```

Expected: branch is pushed.

## Parallelism Rules

Use this concurrency model:

```text
Codex code lane: 1 active feature branch
Multica read-only review lane: 1 active
Multica verifier lane: 1 active
Multica planning/docs lane: 1 active
```

Allowed parallel work:

- Review current Codex diff against a fixed commit SHA.
- Verify current Codex branch in a read-only checkout.
- Refine future issue descriptions in Multica.
- Review docs for contradictions with ADR-0004.

Read-only lane output contract:

```text
Input: branch name + commit SHA + exact acceptance criteria.
Output: Chinese comment or report with pass/blocker/warning.
Repo writes: none.
Branch writes: none.
Blocking power: only P0 correctness, security, data-loss, or product-boundary findings stop a Codex merge.
```

Disallowed parallel work:

- Multiple agents mutating the same worktree.
- Multica agents mutating Ariadne product code in the normal campaign.
- Multica verifier modifying a branch under review.
- Planning/docs lane editing repo docs unless it has a separate branch.
- Auto-merge or auto-push by Ariadne runtime.
- Any write to `main` before checks pass.

Merge serialization:

```text
Merge or fast-forward one branch at a time.
After each merge, update main.
Rebase or recreate the next branch on the new main.
Rerun full verification before pushing an updated branch.
```

## Multica Comment Language

All Multica issue comments, inbox updates, and landing notes for this campaign
must be written in Chinese unless a quoted command output is naturally English.

Required comment shape:

```text
状态：
做了什么：
验证：
风险：
下一步：
```

Do not mark a Multica campaign issue done unless verification output is
recorded. Ariadne product completion is determined by local tests, local
artifacts, and branch state.

## Verification Gates

Focused step gate:

```bash
python3.11 -m pytest <focused-test-file> -q
python3.11 -m ruff check <changed-python-files>
```

Branch-level full gate:

```bash
python3.11 -m pytest
python3.11 -m ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
scripts/verify_v1.sh
git status --short --branch
```

If `uv run ari` is available, also run:

```bash
uv run ari demo full
uv run ari export board
uv run ari backend doctor
```

Clean-state rule:

```text
Generated .ariadne/ output must remain ignored.
Before commit, git status must show only intended source, test, script, or doc changes.
If CLI smoke commands leave unexpected tracked files, inspect and either include intentionally or remove before commit.
```

## Rollback

- Documentation route changes can be reverted with one commit.
- Product code batches are isolated branches; do not merge failed branches.
- If a pushed branch later fails review, push a repair commit to the same
  branch and rerun the branch-level full gate.
- If a branch was merged and then fails, create a revert branch:

```bash
git switch main
git pull --ff-only origin main
git switch -c codex/revert-<short-topic>
git revert <merge_or_commit_sha>
python3.11 -m pytest
python3.11 -m ruff check .
scripts/verify_v1.sh
git push -u origin codex/revert-<short-topic>
```

- If Multica becomes unavailable, continue Codex-led implementation and record
  landing evidence locally in `docs/development_evidence/<branch-name>.md`;
  sync to Multica when it returns.
- If a Multica comment or status is wrong, write a correction comment in
  Chinese instead of rewriting product code or changing local history.

## Self-Review Checklist

- [ ] Plan keeps Ariadne local-first and ticket-centered.
- [ ] Plan does not copy Multica server architecture.
- [ ] Plan stops the old Multica-driven code execution train.
- [ ] Plan preserves Multica as external campaign board/evidence log.
- [ ] Plan gives Codex direct implementation ownership.
- [ ] Plan increases useful parallelism through read-only support lanes.
- [ ] Plan names exact issue batches and issue IDs.
- [ ] Each claimed issue has matching tests or acceptance checks.
- [ ] Plan includes branch chaining and merge serialization.
- [ ] Plan includes verification commands for every code batch.
- [ ] Plan has rollback behavior for pushed branches and external-state failure.
- [ ] Plan has no placeholder implementation phases.
