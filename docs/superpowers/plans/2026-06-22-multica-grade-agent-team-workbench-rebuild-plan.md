# Multica-Grade Agent Team Workbench Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild Ariadne into a Multica-grade local Agent Team Workbench for AI Builders: a real issue-centered agent work-management product, plus Ariadne's upper layer that turns external sources, project goals, feedback, and codebase state into issue changes. The user path must be: create/select project -> add external inputs -> compile issue delta -> confirm issues -> assign agents -> Python daemon/runtime executes Codex/Claude -> diff/tests/review/memory/inbox flow back to the workbench.

**Architecture:** Do not fork Multica and do not migrate to Go/Postgres/auth. Use Multica's product and work-management architecture as the reference shape: issues are the primary work objects, agents are assigned to issues, runtimes claim assignments, progress and blockers are visible, and issue detail is the central collaboration surface. Ariadne keeps its local-first Python runtime and adds a Source-to-Issue compiler above the Multica-style workbench.

**Tech Stack:** Python 3.11, FastAPI local API, JSON/JSONL AriadneStore, Typer CLI for operations, React + Vite + TypeScript frontend, browser-driven QA, pytest, ruff. Frontend may adopt TanStack Query if it materially reduces stale state and endpoint coupling; otherwise keep the existing fetch client but split it by feature.

---

## Product Promise

Ariadne is not a demo dashboard. It is a local Agent Team Workbench for AI Builders.

The product must make this path obvious and operable:

```text
AI Builder chooses a local project folder and target version
  -> adds sources: blog, GitHub repo, paper, local docs, current codebase
  -> Ariadne reads sources into typed source artifacts
  -> Ariadne compiles issue delta from goal + sources + codebase state
  -> user confirms the issue set
  -> Build Lead routes issues to Codex / Claude / reviewer / human
  -> Python daemon claims assignments
  -> Codex / Claude execute against the target repo
  -> diff, tests, review, comments, blockers, memory, and next issues return to the workbench
```

The default screen should feel like Multica's issue workbench, not like a project report. `Project Version Delivery` remains an overview, but the primary operating surface is `Issues`.

## Multica Reference Files To Keep Open During Implementation

Study these files directly before implementing each matching surface:

- `/Users/martinlos/code/multica/packages/views/layout/app-sidebar.tsx`
- `/Users/martinlos/code/multica/packages/views/issues/components/issues-page.tsx`
- `/Users/martinlos/code/multica/packages/views/issues/components/board-view.tsx`
- `/Users/martinlos/code/multica/packages/views/issues/components/issue-detail.tsx`
- `/Users/martinlos/code/multica/packages/views/agents/components/agents-page.tsx`
- `/Users/martinlos/code/multica/packages/views/runtimes/components/runtimes-page.tsx`
- `/Users/martinlos/code/multica/server/migrations/055_task_lease_and_retry.up.sql`
- `/Users/martinlos/code/multica/server/internal/handler/task_lifecycle.go`
- `/Users/martinlos/code/multica/server/cmd/multica/cmd_daemon.go`

Do not copy Multica's Go runtime or server shape. Copy product lessons, interaction patterns, data relationships, and lifecycle semantics where they fit Ariadne.

## Non-Negotiable Boundaries

- [ ] Keep Ariadne local-first and single-user for v1.x.
- [ ] Keep runtime / daemon implementation in Python.
- [ ] Do not fork Multica.
- [ ] Do not migrate to Postgres, hosted auth, SaaS workspace tenancy, or WebSocket-heavy server architecture unless a later product decision explicitly changes v1.x scope.
- [ ] Do not put `demo`, `fake-codex`, or fixture data on the product path.
- [ ] External execution and writes remain gated in code, but the workbench confirms runtime capability once and should not ask normal users to pass low-level flags per issue.
- [ ] Do not claim Codex, Claude, Feishu, GitHub, or external execution worked unless a recorded evidence artifact proves it.

---

## Target Information Architecture

Replace the current delivery-first navigation with a Multica-like workbench shell:

```text
Issues              primary board/list/detail
Inbox               blockers, repair requests, review failures, human-needed items
Projects            local project folders, goals, versions, repo status
Sources             external inputs and typed artifacts
Issue Factory       issue delta preview, rationale, apply history
Agents              Codex, Claude, reviewer, knowledge/repo agents, model/runtime settings
Build Teams         reusable assignment presets / squads
Runtimes            local daemon, machine capability, queues, active runs
Skills              handoff skills, allowed capabilities, execution constraints
Diagnostics         product doctor and integration evidence
Delivery Overview   current version progress summary, not the default surface
```

The sidebar should expose this structure directly. The default route should be `#issues`.

---

## Phase 1: Product Language And IA Foundation

**Purpose:** Stop presenting Ariadne as a demo/report app. Establish the product shell and default operating surface before deeper backend work.

**Files:**

- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/App.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/styles.css`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/types.ts`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/shared/api/types.ts`
- `/Users/martinlos/code/Ariadne/docs/architecture/ariadne_multica_grade_workbench_architecture.md`
- `/Users/martinlos/code/Ariadne/README.md`

**Implementation Steps:**

- [ ] Add architecture note `docs/architecture/ariadne_multica_grade_workbench_architecture.md` with the final product statement: Multica-grade issue workbench + Ariadne Source-to-Issue compiler + Python runtime.
- [ ] Replace delivery-first route model with a stable route map:

  ```ts
  type PageKey =
    | "issues"
    | "inbox"
    | "projects"
    | "sources"
    | "issue-factory"
    | "agents"
    | "build-teams"
    | "runtimes"
    | "skills"
    | "diagnostics"
    | "delivery";
  ```

- [ ] Make `#issues` the default route.
- [ ] Rename visible UI from internal implementation terms to user-operable terms:
  - `项目输入` -> `Sources`
  - `任务建议` -> `Issue Factory`
  - `执行任务` -> `Issues`
  - `版本工作台` -> `Delivery Overview`
- [ ] Move the current `Delivery` summary out of the primary route and into `Delivery Overview`.
- [ ] Remove product-path language implying `demo full`, `fake-codex`, fixture mode, or static data.
- [ ] Keep existing API calls intact in this phase; this is a shell and language correction only.

**Acceptance Criteria:**

- [ ] Opening `http://127.0.0.1:8766/#issues` shows the primary product surface.
- [ ] Opening without a hash redirects/renders `#issues`.
- [ ] Sidebar communicates the product job: issues, agents, runtimes, sources, inbox.
- [ ] No primary CTA points users toward a demo or fixture path.

**Verification Commands:**

```bash
cd /Users/martinlos/code/Ariadne/frontend/ariadne-workbench
npm run build
```

---

## Phase 2: Multica-Style API Projections

**Purpose:** Stop forcing the frontend to reverse-engineer one giant `/api/workbench` object. Add page-specific read models that match the issue workbench mental model.

**Files:**

- `/Users/martinlos/code/Ariadne/ariadne_ltb/interfaces/http/routes.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/workbench_issues.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/workbench_issue_detail.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/workbench_agents.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/workbench_runtimes.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/workbench_projects.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/workbench_task_snapshot.py`
- `/Users/martinlos/code/Ariadne/tests/test_multica_grade_workbench_api.py`
- `/Users/martinlos/code/Ariadne/tests/test_frontend_api_contract_static.py`

**Endpoint Shape:**

```text
GET    /api/issues
GET    /api/issues/{issue_id_or_key}
PATCH  /api/issues/{issue_id_or_key}
POST   /api/issues/{issue_id_or_key}/comments
GET    /api/issues/{issue_id_or_key}/timeline
POST   /api/issues/{issue_id_or_key}/assign
POST   /api/issues/{issue_id_or_key}/rerun
GET    /api/agent-task-snapshot
GET    /api/projects
GET    /api/projects/{project_id}
GET    /api/agents
PATCH  /api/agents/{agent_id}
GET    /api/runtimes
GET    /api/skills
```

**Implementation Steps:**

- [ ] Add `IssueListItem` projection with `id`, `key`, `title`, `status`, `priority`, `assignee`, `project`, `targetVersion`, `sourceCount`, `evidenceCount`, `lastRunStatus`, `reviewVerdict`, `blockedReason`, and `updatedAt`.
- [ ] Add `IssueDetail` projection with issue body, evidence, source links, route decision, handoff path, comments, timeline, assignment list, execution results, review, diff/test summary, next issue links.
- [ ] Add `AgentTaskSnapshot` projection inspired by Multica's agent task snapshot: active assignment, queued count, blocked count, heartbeat, current issue key, current backend, last event.
- [ ] Add `RuntimeListItem` projection: runtime id/name, daemon state, external execution capability, Codex availability, Claude availability, queue depth, active assignment.
- [ ] Add `AgentListItem` projection: agent id/name/role/backend/model or CLI, routing purpose, active assignment count, blocked count, configurable fields.
- [ ] Add `ProjectListItem` projection: local path, git status, target version, source count, issue counts, last run.
- [ ] Keep existing `/api/workbench` for backward compatibility during transition; mark it as legacy in code comments only where useful.
- [ ] Add contract tests for all new endpoints using local fixture store only.

**Acceptance Criteria:**

- [ ] Frontend can render Issues, Issue Detail, Agents, Runtimes, Projects without reading unrelated global DTO fields.
- [ ] Contract tests fail if endpoint field names drift.
- [ ] Existing daemon, assignment, source, and issue-factory tests still pass.

**Verification Commands:**

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m pytest \
  tests/test_multica_grade_workbench_api.py \
  tests/test_control_plane_http.py \
  tests/test_workbench_daemon_feedback.py \
  tests/test_frontend_api_contract_static.py
ruff check .
```

---

## Phase 3: Issues Workbench Rebuild

**Purpose:** Rebuild the primary user surface around issues, not around internal system pages.

**Files:**

- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/App.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/app/routes.ts`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/app/shell/AppShell.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/issues/IssuesPage.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/issues/IssueBoard.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/issues/IssueList.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/issues/IssueDetail.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/widgets/issue-detail/IssueActivity.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/widgets/issue-detail/IssueEvidence.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/widgets/issue-detail/IssueExecution.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/widgets/issue-detail/IssueComments.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/shared/api/client.ts`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/shared/api/types.ts`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/styles.css`

**Implementation Steps:**

- [ ] Split monolithic `App.tsx` into shell, route resolver, and pages.
- [ ] Build issue board columns by status: Backlog, Ready, Assigned, Running, Review, Blocked, Done.
- [ ] Add compact issue cards with key, title, priority, assignee/backend, run state, review state, evidence count, and blocked marker.
- [ ] Add issue list view for users who prefer dense scanning.
- [ ] Add issue detail route `#issues/<issue_key_or_id>`.
- [ ] In issue detail, show:
  - [ ] title/body/status/priority/project
  - [ ] evidence/source references
  - [ ] route decision
  - [ ] handoff packet
  - [ ] assignments and active run
  - [ ] execution log
  - [ ] changed files and diff summary
  - [ ] tests
  - [ ] review verdict
  - [ ] comments and timeline
  - [ ] next issues
- [ ] Add primary issue actions:
  - [ ] assign to agent
  - [ ] run now
  - [ ] rerun
  - [ ] add comment
  - [ ] open target project path
  - [ ] open evidence artifacts
- [ ] Remove static placeholder copy where a real API state should be shown.

**Acceptance Criteria:**

- [ ] A user can land on Issues and understand what work exists, what is running, what is blocked, and what can be assigned.
- [ ] A user can open one issue and see the full chain from source evidence to execution and review.
- [ ] Empty states point to real product actions: add source, create project, start runtime, assign issue.
- [ ] No issue surface depends on hand-written fixture data.

**Verification Commands:**

```bash
cd /Users/martinlos/code/Ariadne/frontend/ariadne-workbench
npm run build
```

Browser QA:

```text
Open http://127.0.0.1:8766/#issues
Open http://127.0.0.1:8766/#issues/ARI-003
Verify board/list/detail all read real API state.
```

---

## Phase 4: Agents, Build Teams, Runtimes, And Skills

**Purpose:** Turn agent/team/runtime pages from static display into operable Multica-like control surfaces.

**Files:**

- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/agents/AgentsPage.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/build-teams/BuildTeamsPage.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/runtimes/RuntimesPage.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/skills/SkillsPage.tsx`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/workbench_agents.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/workbench_runtimes.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/runtime/daemon.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/runtime/capabilities.py`
- `/Users/martinlos/code/Ariadne/tests/test_workbench_agents_runtimes.py`

**Implementation Steps:**

- [ ] Agents page shows real agents from store/config: Codex, Claude Code, Reviewer, Knowledge Agent, Repo Understanding Agent, Issue Factory Agent, Build Lead, Handoff Agent, Memory Agent.
- [ ] Each agent card shows role, backend, capability, active assignment, blocked count, and current runtime compatibility.
- [ ] Add safe configuration actions where supported: backend preference, model/provider name, reasoning level, enabled/disabled.
- [ ] Build Teams page defines reusable routing presets:
  - [ ] Codex Builder + Reviewer
  - [ ] Claude Builder + Reviewer
  - [ ] Knowledge + Repo + Issue Factory
  - [ ] Human Review Required
- [ ] Runtimes page shows local daemon status, active assignment, queue, heartbeat, Codex/Claude availability, external execution capability, and last error.
- [ ] Runtimes page actions:
  - [ ] start daemon
  - [ ] stop daemon
  - [ ] refresh capability
  - [ ] claim next assignment if daemon is idle
- [ ] Skills page shows BuildSkill packs, linked agents, allowed paths, output expectations, and handoff references.
- [ ] Skills page supports linking a skill to an issue/handoff where the backend already supports it.

**Acceptance Criteria:**

- [ ] User can see which agents can actually run and why.
- [ ] User can start/stop runtime from the workbench.
- [ ] User can assign an issue to a real backend-compatible agent without reading CLI docs.
- [ ] Runtime capability contradictions are removed: one status model drives both agent and runtime pages.

**Verification Commands:**

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m pytest tests/test_workbench_agents_runtimes.py tests/test_backend_doctor.py
ruff check .
cd /Users/martinlos/code/Ariadne/frontend/ariadne-workbench
npm run build
```

---

## Phase 5: Ariadne Upper Layer: Sources And Issue Factory

**Purpose:** Keep Ariadne's unique value clear: external inputs and feedback change the issue set. This layer must feed the issue workbench, not live as a disconnected form.

**Files:**

- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/sources/SourcesPage.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/issue-factory/IssueDeltaPage.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/features/project-inputs/*`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/source_ingestion.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/source_analysis.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/issue_factory.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/domain/source_artifacts.py`
- `/Users/martinlos/code/Ariadne/tests/test_source_to_issue_compiler.py`
- `/Users/martinlos/code/Ariadne/tests/test_issue_factory_http.py`

**Implementation Steps:**

- [ ] Treat input as `Source`, not always as `Knowledge Card`.
- [ ] For URL/blog/paper/local markdown, generate `KnowledgeArtifact`.
- [ ] For GitHub repo/local repo, generate `RepositoryUnderstandingArtifact`.
- [ ] For current project scan, generate `CodebaseStateArtifact`.
- [ ] The Sources page should allow the user to paste a raw link first; title/type/summary are optional overrides, not required first fields.
- [ ] Saving a source should immediately show a visible state: queued, analyzing, analyzed, failed.
- [ ] Analysis should produce a clear artifact page/card showing:
  - [ ] source type
  - [ ] fetch/clone status
  - [ ] files or content inspected
  - [ ] evidence extracted
  - [ ] relevance to project goal
  - [ ] generated artifact path
- [ ] Issue Factory reads project goal + typed source artifacts + codebase state.
- [ ] Issue Factory generates an issue delta with add/update/deprioritize/defer/reject actions.
- [ ] Each issue delta item must include evidence and acceptance criteria.
- [ ] Applying issue delta creates or updates issues in the Issues board.
- [ ] Stale preview errors become recoverable UI states: refresh preview, compare changed backlog, discard preview.

**Acceptance Criteria:**

- [ ] User pastes a GitHub repo URL and sees repository understanding, not just a README summary.
- [ ] User pastes a blog URL and sees knowledge evidence.
- [ ] User sees where a source went after saving.
- [ ] Applying issue delta lands work in Issues with evidence attached.
- [ ] No `500` for stale preview; the UI offers refresh/apply-again flow.

**Verification Commands:**

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m pytest tests/test_source_to_issue_compiler.py tests/test_issue_factory_http.py
ruff check .
cd /Users/martinlos/code/Ariadne/frontend/ariadne-workbench
npm run build
```

---

## Phase 6: Execution Evidence, Recovery, And Lifecycle Hardening

**Purpose:** Make the workbench feel like a real agent operations product: assignments are claimed, progress is visible, blocked states are actionable, and results flow back to the issue.

**Files:**

- `/Users/martinlos/code/Ariadne/ariadne_ltb/runtime/daemon.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/runtime/assignment_runner.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/runtime/backends.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/assignment_service.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/inbox_service.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/progress_events.py`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/inbox/InboxPage.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/widgets/issue-detail/IssueExecution.tsx`
- `/Users/martinlos/code/Ariadne/tests/test_assignment_lifecycle.py`
- `/Users/martinlos/code/Ariadne/tests/test_inbox_actions_http.py`
- `/Users/martinlos/code/Ariadne/tests/test_execution_evidence_flow.py`

**Implementation Steps:**

- [ ] Align assignment lifecycle with Multica-style lease/retry semantics while keeping JSON persistence:
  - [ ] queued
  - [ ] claimed
  - [ ] running
  - [ ] review
  - [ ] blocked
  - [ ] failed
  - [ ] done
- [ ] Add heartbeat and stale assignment recovery for local daemon.
- [ ] Add typed failure reasons:
  - [ ] missing_runtime_capability
  - [ ] missing_external_execution_gate
  - [ ] target_repo_invalid
  - [ ] dirty_worktree_blocked
  - [ ] command_unavailable
  - [ ] execution_failed
  - [ ] tests_failed
  - [ ] review_failed
  - [ ] stale_issue_delta
- [ ] Ensure every assignment writes progress events that issue detail can display.
- [ ] Ensure Codex/Claude backend results write:
  - [ ] handoff path
  - [ ] stdout/stderr
  - [ ] exit code
  - [ ] changed files
  - [ ] diff
  - [ ] test command and result
  - [ ] review artifact
  - [ ] memory artifact
  - [ ] next issue artifact
- [ ] Inbox actions must be real:
  - [ ] create repair issue
  - [ ] rerun assignment
  - [ ] acknowledge blocker
  - [ ] assign to human
  - [ ] link blocker back to issue detail
- [ ] The daemon should not抢跑 old work when the user dispatches a current issue from detail. Current issue actions should create explicit high-priority assignment or run-now path bound to that issue.

**Acceptance Criteria:**

- [ ] User can tell exactly what the daemon is doing and which issue it is working on.
- [ ] Running an issue shows progress events in the issue detail without refreshing unrelated pages.
- [ ] Blocked states are actionable from Inbox and issue detail.
- [ ] A failed assignment can produce a repair issue or rerun without using CLI.

**Verification Commands:**

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m pytest \
  tests/test_assignment_lifecycle.py \
  tests/test_inbox_actions_http.py \
  tests/test_execution_evidence_flow.py \
  tests/test_workbench_daemon_feedback.py
ruff check .
```

---

## Phase 7: Dogfood Closure Through Browser Only

**Purpose:** Prove Ariadne can be used as intended by an AI Builder from the browser: external inputs -> issue factory -> real agent assignment -> Codex/Claude execution -> evidence returns -> target project advances.

**Files:**

- `/Users/martinlos/code/Ariadne/docs/dogfood/2026-06-18-mini-code-agent-web-dogfood.md`
- `/Users/martinlos/code/Ariadne/docs/dogfood/2026-06-22-multica-grade-workbench-dogfood-result.md`
- `/Users/martinlos/code/Ariadne/docs/development_report.md`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/e2e/multica-grade-workbench.spec.ts`
- `/Users/martinlos/code/Ariadne/scripts/verify_product_closure.sh`

**Dogfood Scenario:**

Use the browser, not the CLI, to create or select a local target project for a mini coding agent.

External inputs:

- `https://minimal-agent.com/`
- `https://github.com/SWE-agent/mini-swe-agent`
- `https://github.com/e10nMa2k/cc-mini`

Expected user path:

```text
Open Workbench
  -> Projects: create/select local target project folder
  -> Sources: paste the three external inputs
  -> Sources: analyze inputs into typed artifacts
  -> Issue Factory: generate issue delta for v0.1
  -> Issue Factory: apply issue delta
  -> Issues: inspect generated MCA issues
  -> Issue Detail: assign first implementation issue to Codex or Claude
  -> Runtimes: start/connect daemon
  -> Issue Detail: watch assignment/progress/evidence
  -> Target repo: verify code changed
  -> Issue Detail: verify diff/tests/review/memory/next issue
```

**Implementation Steps:**

- [ ] Add a browser dogfood script or documented manual run with screenshots/evidence paths.
- [ ] Ensure the dogfood target project is not confused with Ariadne's own repo.
- [ ] Ensure generated issues are target-project issues, not Ariadne-internal ARI roadmap tasks.
- [ ] Run Codex/Claude only when local gates and credentials are satisfied.
- [ ] If Codex/Claude cannot run, record the exact product blocker in the issue/inbox and dogfood result; do not mark closure as achieved.
- [ ] Update development report with actual evidence.

**Acceptance Criteria:**

- [ ] The dogfood result document records browser steps, target project path, sources, generated issues, assigned issue, backend, run result, changed files, test result, review, memory, and next issue.
- [ ] If real execution succeeds, target project has a runnable v0.1 artifact.
- [ ] If real execution is blocked, the block is visible in Workbench and actionable, not hidden in logs.
- [ ] No command-line-only workaround is required for the normal user path.

**Verification Commands:**

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m pytest
ruff check .
cd /Users/martinlos/code/Ariadne/frontend/ariadne-workbench
npm run build
```

Browser QA:

```text
Open http://127.0.0.1:8766/#issues
Open http://127.0.0.1:8766/#projects
Open http://127.0.0.1:8766/#sources
Open http://127.0.0.1:8766/#issue-factory
Open http://127.0.0.1:8766/#runtimes
Open http://127.0.0.1:8766/#inbox
Complete the mini-code-agent dogfood without using Ariadne CLI.
```

---

## Migration Strategy

- [ ] Keep current APIs and pages working until their replacements pass browser QA.
- [ ] Do not destructively rewrite existing `.ariadne` project data.
- [ ] Add projection endpoints before deleting frontend assumptions.
- [ ] Make the issue board work on existing tickets before adding richer issue factory behavior.
- [ ] Keep `demo full` and `fake-codex` only as regression/offline fixtures, not as product navigation or primary docs.

## Risks And Mitigations

- [ ] **Risk:** Frontend rewrite creates a prettier but still disconnected app.
  - **Mitigation:** Each phase must pass a browser action path, not just build.
- [ ] **Risk:** API projections duplicate logic and drift.
  - **Mitigation:** Centralize projections in `ariadne_ltb/application/workbench_*` and keep routes thin.
- [ ] **Risk:** Codex/Claude execution is unavailable during development.
  - **Mitigation:** Product must show actionable blocked state; tests stay deterministic; closure is not claimed without evidence.
- [ ] **Risk:** Issue Factory stays template-driven.
  - **Mitigation:** Source artifacts must include inspected files/content and evidence; issue delta must cite those artifacts.
- [ ] **Risk:** Ariadne loses its identity by copying Multica too closely.
  - **Mitigation:** Multica-style workbench is the substrate; Ariadne-specific value is Sources -> Issue Delta -> Project Version progress.

## Full Verification Gate

Run after each independently mergeable phase:

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m pytest
ruff check .
cd /Users/martinlos/code/Ariadne/frontend/ariadne-workbench
npm run build
```

Run before claiming product closure:

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m pytest
ruff check .
python3.11 -m ariadne_ltb.cli doctor product
cd /Users/martinlos/code/Ariadne/frontend/ariadne-workbench
npm run build
```

Then complete browser QA from `#issues` through the mini-code-agent dogfood. The final result must be documented in:

```text
/Users/martinlos/code/Ariadne/docs/dogfood/2026-06-22-multica-grade-workbench-dogfood-result.md
```

## Implementation Order

Use one branch per large phase if working with separate agents. If one Codex thread implements the full plan, keep commits phase-scoped:

```text
phase 1 commit: IA and product language
phase 2 commit: API projections
phase 3 commit: issues workbench
phase 4 commit: agents/runtimes/skills surfaces
phase 5 commit: source-to-issue integration
phase 6 commit: lifecycle and recovery
phase 7 commit: dogfood closure evidence
```

Do not merge a phase if its acceptance criteria are only partially satisfied. Record the gap as an inbox/blocker or implementation issue.
