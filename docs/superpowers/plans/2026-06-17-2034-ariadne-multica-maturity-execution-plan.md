# Ariadne Multica Maturity Execution Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring Ariadne to Multica-level local agent work-management maturity while keeping it Python, local-first, single-user, deterministic, and safety-gated.

**Architecture:** Ariadne remains a Ticket-centered Agent Workbench. The product absorbs Multica's issue, agent, runtime, skill, resource, progress, review, inbox, and board model without copying Multica's hosted server stack. New work lands as small vertical slices with tests, local verification, commits, pushes, and Chinese progress evidence.

**Tech Stack:** Python 3.11+, Pydantic v2, Typer, Pytest, Ruff, JSON/JSONL persistence, local Git worktrees, optional Vite React workbench only when integrating the existing frontend branch.

---

## Operating Rules

This plan is the detailed execution companion for:

```text
docs/goals/2026-06-17-2034-ariadne-multica-maturity-goal.md
```

Authoritative context:

```text
docs/ops/ARIADNE_MULTICA_MATURITY_ROADMAP.md
docs/adr/ADR-0004-ticket-centered-agent-workbench.md
docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md
docs/ops/CODEX_NON_FRONTEND_SECTION_PLAN.md
docs/architecture/multica_architecture_digest.md
docs/architecture/ariadne_multica_gap_report.md
```

Hard boundaries:

- Do not revive BuildGoal-first architecture.
- Do not fork or copy Multica code.
- Do not introduce Go, Postgres, hosted auth, multi-tenancy, or WebSocket collaboration for v1.x.
- Do not add default auto-commit, auto-push, auto-merge, or PR creation inside Ariadne runtime.
- Do not require Codex, Claude, DeepSeek, Feishu, GitHub token, network, or Multica for automated tests.
- Do not develop new frontend features as part of this goal.
- Frontend changes are allowed only for integration conflict resolution or stable backend data contracts needed by the existing frontend branch.

Branch facts at plan creation:

```text
core branch: codex/ariadne-core-orchestration-backends-3
frontend branch: codex/ariadne-workbench-frontend-lane
recommended integration branch: codex/ariadne-core-frontend-integration
```

The frontend branch was previously built as a demo/local workbench lane. Codex must decide when to integrate it by checking current branch state, conflicts, and verification results. Do not merge it independently into `main`.

## Required Verification

For every non-doc code slice:

```bash
python3.11 -m pytest
python3.11 -m ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
scripts/verify_v1.sh
```

For integration touching the existing frontend branch:

```bash
npm --prefix frontend/ariadne-workbench run build
```

For docs-only slices:

```bash
git diff --check
```

Each slice ends with:

```bash
git status --short --branch
git diff --stat
git diff --check
git add ariadne_ltb tests README.md docs/development_report.md docs/ops docs/superpowers/plans docs/goals scripts frontend/ariadne-workbench
git commit -m "feat: land verified Ariadne maturity slice"
git push
```

If a listed path does not exist in the current slice, omit that path from the
`git add` command. Do not stage unrelated dirty files.

Write Chinese progress evidence after each landed slice:

```text
状态：
分支：
commit：
改动文件：
验证命令：
结果：
风险：
下一步：
```

## File Responsibility Map

Core runtime and domain:

- `ariadne_ltb/models.py`: domain models and lifecycle fields.
- `ariadne_ltb/storage.py`: local JSON/JSONL persistence and migrations.
- `ariadne_ltb/orchestrator.py`: reusable full ticket execution loop.
- `ariadne_ltb/daemon.py`: assignment claim, heartbeat, runtime loop.
- `ariadne_ltb/execution.py`: backend adapters and execution results.
- `ariadne_ltb/runtime.py`: runtime capability and journal surfaces.
- `ariadne_ltb/permissions.py`: execution permission profiles.
- `ariadne_ltb/retry.py`: retry, backoff, dead-letter, and recovery policies.
- `ariadne_ltb/review.py`: conservative review and future risk scoring.
- `ariadne_ltb/memory.py`: memory write and retrieval.
- `ariadne_ltb/backlog.py`: ticket backlog update decisions.
- `ariadne_ltb/board.py`: static board export and board data sections.
- `ariadne_ltb/cli.py`: user-facing commands and JSON outputs.

Likely new modules:

- `ariadne_ltb/resources.py`: typed project resource boundaries.
- `ariadne_ltb/inbox.py`: blocker and follow-up inbox records.
- `ariadne_ltb/search.py`: local search index over tickets, comments, memory, artifacts, reviews, and inbox.
- `ariadne_ltb/approval.py`: manual approval checkpoints.
- `ariadne_ltb/store_migrations.py`: schema version and read migrations.
- `ariadne_ltb/workdir_policy.py`: workdir reuse and cleanup policy.
- `ariadne_ltb/evidence.py`: release evidence packet helpers if not already sufficient.

Frontend branch:

- `frontend/ariadne-workbench/*`: existing local workbench only.
- Modify frontend files only during integration or when a core data contract requires a minimal adapter update.

Docs and reports:

- `README.md`
- `docs/development_report.md`
- `docs/ops/ARIADNE_MULTICA_MATURITY_ROADMAP.md`
- `docs/superpowers/plans/2026-06-17-2034-ariadne-multica-maturity-execution-plan.md`

## Task 1: Re-check Current State

**Files:**
- Modify: none

- [ ] **Step 1: Confirm core branch state**

Run:

```bash
cd /Users/martinlos/code/Ariadne.worktrees/ariadne-core-orchestration-backends-3
git fetch --all --prune
git status --short --branch
git log --oneline -8
```

Expected:

- Current branch is `codex/ariadne-core-orchestration-backends-3` or a deliberate successor.
- Worktree is clean before starting a new slice.
- If dirty files exist, classify them before editing.

- [ ] **Step 2: Confirm frontend branch state**

Run:

```bash
cd /Users/martinlos/code/Ariadne
git fetch --all --prune
git status --short --branch
git log --oneline -8
```

Expected:

- Current branch is `codex/ariadne-workbench-frontend-lane` or a deliberate successor.
- Worktree is clean.
- Do not edit frontend files during this check.

- [ ] **Step 3: Compare branches**

Run from either worktree:

```bash
git log --left-right --cherry-pick --oneline main...codex/ariadne-core-orchestration-backends-3
git log --left-right --cherry-pick --oneline main...codex/ariadne-workbench-frontend-lane
git diff --name-only codex/ariadne-core-orchestration-backends-3...codex/ariadne-workbench-frontend-lane | sort
```

Expected:

- Identify whether integration is still required.
- If the frontend branch has already been merged elsewhere, skip Task 2 and record evidence.

## Task 2: Decide And Execute Branch Integration

**Files:**
- Modify: conflict files only.
- Likely conflict files: `README.md`, `ariadne_ltb/board.py`, `ariadne_ltb/cli.py`, `ariadne_ltb/execution.py`, `ariadne_ltb/models.py`, `ariadne_ltb/orchestrator.py`, `ariadne_ltb/storage.py`, `docs/development_report.md`, `tests/test_v1_board_ux.py`.

- [ ] **Step 1: Decide whether integration is needed now**

Integrate now if all are true:

```text
core branch is clean
frontend branch is clean
core branch verification passed recently or can pass now
frontend branch build passed recently or can pass now
future roadmap work would touch files already changed by both branches
```

Defer integration only if:

```text
frontend branch is stale or failing
core branch has uncommitted work
integration conflicts would block an urgent safety fix
```

If deferred, write a Chinese evidence note with exact blocker and continue with a non-conflicting core slice.

- [ ] **Step 2: Create integration branch**

Run:

```bash
cd /Users/martinlos/code/Ariadne.worktrees/ariadne-core-orchestration-backends-3
git switch codex/ariadne-core-orchestration-backends-3
git pull --ff-only
git switch -c codex/ariadne-core-frontend-integration
```

Expected:

- New branch starts from the latest core branch.

- [ ] **Step 3: Merge existing frontend branch**

Run:

```bash
git merge codex/ariadne-workbench-frontend-lane
```

Expected:

- If no conflicts, continue.
- If conflicts appear, resolve them manually.
- For Python runtime behavior, prefer the core branch.
- For frontend files under `frontend/ariadne-workbench/`, keep frontend branch additions unless they assume stale core data.

- [ ] **Step 4: Verify combined branch**

Run:

```bash
python3.11 -m pytest
python3.11 -m ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
scripts/verify_v1.sh
npm --prefix frontend/ariadne-workbench run build
```

Expected:

- All commands pass.
- If `scripts/verify_v1.sh` passes but leaves stale `.ariadne` operational state, record it as the next cleanup issue instead of hiding it.

- [ ] **Step 5: Commit and push integration**

Run:

```bash
git status --short --branch
git add README.md ariadne_ltb/board.py ariadne_ltb/cli.py ariadne_ltb/execution.py ariadne_ltb/models.py ariadne_ltb/orchestrator.py ariadne_ltb/storage.py docs/development_report.md tests/test_v1_board_ux.py frontend/ariadne-workbench docs/frontend
git commit -m "chore: integrate core and frontend workbench branches"
git push -u origin codex/ariadne-core-frontend-integration
```

Expected:

- Integration branch is pushed and clean.
- Do not merge to `main` until verification output is recorded.

## Task 3: Resource Boundaries And Execution Safety

**Files:**
- Create: `ariadne_ltb/resources.py`
- Create or modify: `ariadne_ltb/approval.py`
- Modify: `ariadne_ltb/models.py`
- Modify: `ariadne_ltb/storage.py`
- Modify: `ariadne_ltb/execution.py`
- Modify: `ariadne_ltb/orchestrator.py`
- Modify: `ariadne_ltb/board.py`
- Modify: `ariadne_ltb/cli.py`
- Test: `tests/test_project_resources.py`
- Test: `tests/test_approval_checkpoints.py`
- Test: `tests/test_execution_permissions.py`

- [ ] **Step 1: Add failing tests for typed resources**

Tests must cover:

- local directory resource serialization;
- GitHub repo resource serialization;
- memory store resource serialization;
- Feishu space resource serialization as dry-run only;
- invalid resource type rejection;
- target repo must resolve inside an allowed local directory resource.

Run:

```bash
python3.11 -m pytest tests/test_project_resources.py -q
```

Expected before implementation:

- Tests fail because typed resource helpers are missing.

- [ ] **Step 2: Implement resource model and storage**

Implement:

```text
ProjectResource.type
ProjectResource.ref
ProjectResource.permissions
.ariadne/project/resources.json
store.load_project_resources()
store.save_project_resources()
```

Keep JSON deterministic and human-reviewable.

- [ ] **Step 3: Add manual approval checkpoints**

Approval checkpoints must be required for:

- real external execution;
- sensitive path writes;
- Feishu real write;
- resource scope widening.

Persist approval artifacts under:

```text
.ariadne/approvals/
```

Add CLI surfaces:

```bash
ari approval list
APPROVAL_ID=$(ari approval list --output json | python3.11 -c 'import json,sys; data=json.load(sys.stdin); print(data[0]["id"] if data else "")')
test -n "$APPROVAL_ID" && ari approval show "$APPROVAL_ID"
```

Do not add a command that silently approves unsafe actions.

- [ ] **Step 4: Wire board and doctor**

Board and doctor must show:

- project resources;
- permission profile;
- pending approvals;
- external execution gate state;
- Feishu write gate state.

- [ ] **Step 5: Verify and commit**

Run required non-doc verification. Commit:

```bash
git add ariadne_ltb tests README.md docs/development_report.md
git commit -m "feat: add project resource boundaries"
git push
```

## Task 4: Inbox, Blockers, And Local Search

**Files:**
- Create: `ariadne_ltb/inbox.py`
- Create: `ariadne_ltb/search.py`
- Modify: `ariadne_ltb/models.py`
- Modify: `ariadne_ltb/storage.py`
- Modify: `ariadne_ltb/orchestrator.py`
- Modify: `ariadne_ltb/daemon.py`
- Modify: `ariadne_ltb/board.py`
- Modify: `ariadne_ltb/cli.py`
- Test: `tests/test_inbox.py`
- Test: `tests/test_local_search.py`

- [ ] **Step 1: Add failing inbox tests**

Tests must cover:

- blocked execution creates inbox item;
- review follow-up creates inbox item;
- inbox item can be resolved;
- inbox item records ticket key, assignment id, failure reason, evidence path, and next action.

- [ ] **Step 2: Implement inbox persistence**

Persist:

```text
.ariadne/inbox/items/*.json
```

Add CLI:

```bash
ari inbox list
INBOX_ID=$(ari inbox list --output json | python3.11 -c 'import json,sys; data=json.load(sys.stdin); print(data[0]["id"] if data else "")')
test -n "$INBOX_ID" && ari inbox show "$INBOX_ID"
test -n "$INBOX_ID" && ari inbox resolve "$INBOX_ID" --note "resolved after evidence review"
```

- [ ] **Step 3: Add local search tests**

Search must cover:

- tickets;
- comments;
- memory;
- artifacts;
- review reports;
- inbox records.

Add CLI:

```bash
ari search "export-json blocker"
ari search "review verdict" --output json
```

- [ ] **Step 4: Implement local lexical search**

Do not add vector DB or network dependency.

Search result fields:

```text
kind
id
ticket_key
title
snippet
path
score
```

- [ ] **Step 5: Board and verification**

Board must show latest inbox and search index summary. Run required verification and commit:

```bash
git commit -m "feat: add local inbox and search"
```

## Task 5: Review And Acceptance Quality

**Files:**
- Modify: `ariadne_ltb/review.py`
- Modify: `ariadne_ltb/models.py`
- Modify: `ariadne_ltb/orchestrator.py`
- Modify: `ariadne_ltb/board.py`
- Modify: `ariadne_ltb/cli.py`
- Test: `tests/test_review_risk_scoring.py`
- Test: `tests/test_acceptance_quality_gate.py`

- [ ] **Step 1: Add failing risk scoring tests**

Tests must cover:

- passing run with covered criteria gets low risk;
- changed files without matching acceptance evidence gets medium or high risk;
- failed tests produce high risk;
- blocked execution cannot be marked done.

- [ ] **Step 2: Add acceptance coverage model**

Review report must include:

```text
criterion
status: covered | failed | waived | not_applicable | missing
evidence_refs
risk
```

- [ ] **Step 3: Enforce status transition gate**

Ticket cannot move to done if required acceptance criteria are missing evidence.

- [ ] **Step 4: Surface review evidence**

CLI and board must show:

- risk score;
- acceptance coverage table;
- failed checks;
- follow-up tickets.

- [ ] **Step 5: Verify and commit**

Run required verification. Commit:

```bash
git commit -m "feat: add review risk scoring"
```

## Task 6: Workdir Reuse, Cleanup, And Store Durability

**Files:**
- Create: `ariadne_ltb/workdir_policy.py`
- Create: `ariadne_ltb/store_migrations.py`
- Modify: `ariadne_ltb/worktrees.py`
- Modify: `ariadne_ltb/storage.py`
- Modify: `ariadne_ltb/store_doctor.py`
- Modify: `ariadne_ltb/cli.py`
- Modify: `scripts/verify_v1.sh`
- Test: `tests/test_workdir_policy.py`
- Test: `tests/test_store_migrations.py`
- Test: `tests/test_verify_script_isolation.py`

- [ ] **Step 1: Add failing cleanup tests**

Tests must cover:

- active isolated worktree is not deleted;
- stale completed isolated worktree can be listed;
- stale blocked worktree produces resume or cleanup recommendation;
- cleanup command requires explicit confirmation.

- [ ] **Step 2: Implement workdir policy**

Add CLI:

```bash
ari workdir list
ari workdir cleanup --confirm-cleanup
```

Do not delete worktrees without explicit confirmation.

- [ ] **Step 3: Add store schema version**

Persist:

```text
.ariadne/store_version.json
```

Store doctor must report:

```text
schema_version
migration_needed
corruption_count
stale_operational_state_count
```

- [ ] **Step 4: Isolate verification script**

Change `scripts/verify_v1.sh` so repeated runs do not accumulate blocked assignments in the repository root. Preferred behavior:

```text
use a temporary --root for destructive demo/daemon checks
keep source checkout clean
print generated board path
```

- [ ] **Step 5: Verify and commit**

Run required verification twice in a row. Commit:

```bash
git commit -m "feat: add workdir cleanup and store durability"
```

## Task 7: Board, CLI, And Existing Web Workbench Parity

**Files:**
- Modify: `ariadne_ltb/board.py`
- Modify: `ariadne_ltb/cli.py`
- Modify: `ariadne_ltb/storage.py`
- Modify: `frontend/ariadne-workbench/*` only if integrating existing frontend data contracts requires it.
- Test: `tests/test_board_parity.py`
- Test: `tests/test_cli_json_contracts.py`
- Test: frontend tests if present.

- [ ] **Step 1: Define parity contract**

CLI JSON, static board, and existing web workbench must agree on:

- ticket status;
- assignment state;
- runtime capability;
- project resources;
- route decision;
- progress events;
- inbox blockers;
- review verdict and risk;
- memory paths;
- next tickets.

- [ ] **Step 2: Add parity tests**

Tests must generate a local run and compare CLI JSON output with board data files.

- [ ] **Step 3: Update existing frontend only if necessary**

Allowed frontend changes:

- read a new stable `.ariadne` JSON field;
- adapt to renamed core field after integration;
- fix build failure caused by core data contract changes.

Not allowed:

- new frontend-only feature;
- broad visual redesign;
- hosted server dependency.

- [ ] **Step 4: Verify and commit**

Run required backend verification and frontend build if frontend files changed. Commit:

```bash
git commit -m "feat: align board and workbench data contracts"
```

## Task 8: Dogfood Scenario And Release Evidence

**Files:**
- Create or modify: `ariadne_ltb/evidence.py`
- Modify: `ariadne_ltb/cli.py`
- Modify: `docs/demo/ARIADNE_V1_DEMO_SCRIPT.md`
- Modify: `docs/evaluation/v1_0_evaluation.md`
- Modify: `docs/development_report.md`
- Test: `tests/test_release_evidence.py`

- [ ] **Step 1: Define dogfood scenario**

Scenario must start from source docs and end with:

- updated ticket backlog;
- assignment;
- daemon run;
- execution result;
- diff or blocked evidence;
- review;
- memory;
- next tickets;
- board;
- release evidence packet.

- [ ] **Step 2: Add release evidence packet command**

Add CLI:

```bash
ari evidence packet
ari evidence packet --output json
```

Evidence packet must include:

```text
commands run
ticket keys
assignment ids
run ids
changed files
test results
review verdicts
memory paths
next ticket paths
board path
known limitations
safety gate state
```

- [ ] **Step 3: Verify no external credentials required**

Run dogfood with `fake-codex` by default. Real Codex remains optional and gated.

- [ ] **Step 4: Verify and commit**

Run full verification. Commit:

```bash
git commit -m "feat: add dogfood release evidence"
```

## Task 9: Final Roadmap Review

**Files:**
- Modify: `README.md`
- Modify: `docs/development_report.md`
- Modify: `docs/ops/ARIADNE_MULTICA_MATURITY_ROADMAP.md`

- [ ] **Step 1: Re-read roadmap**

Confirm every phase in `docs/ops/ARIADNE_MULTICA_MATURITY_ROADMAP.md` is either implemented, explicitly deferred, or blocked with evidence.

- [ ] **Step 2: Run final verification**

Run:

```bash
python3.11 -m pytest
python3.11 -m ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
scripts/verify_v1.sh
npm --prefix frontend/ariadne-workbench run build
```

If frontend package is not present because frontend integration was deliberately deferred, record the exact reason and omit only the npm command.

- [ ] **Step 3: Write final Chinese summary**

Include:

```text
完成了哪些 Multica 对标能力
哪些 Ariadne 差异化能力已经可用
哪些能力仍然 deferred
真实 Codex 是否仍然 gated
是否需要合并 main
下一张推荐 Build Ticket
```

- [ ] **Step 4: Commit and push final docs**

Run:

```bash
git add README.md docs/development_report.md docs/ops/ARIADNE_MULTICA_MATURITY_ROADMAP.md
git commit -m "docs: summarize Multica maturity progress"
git push
```

## Self-Review Checklist For Future Codex

Before claiming completion, answer:

- Did Ariadne remain Ticket-centered?
- Did the work improve issue/agent/runtime/board maturity?
- Did knowledge, feedback, codebase state, or review update the ticket backlog?
- Did the feature add visible evidence for AI Builder users?
- Did the feature avoid default external execution?
- Did tests run without external services?
- Did the branch get committed and pushed?
- Did Chinese progress evidence get written?

If any answer is no, do not claim the goal is complete.
