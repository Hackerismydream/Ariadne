# Ariadne Agent Control Plane Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Review what Ariadne must change to let AI builders operate agent teams from the frontend, not just from the CLI.

**Architecture:** The review treats Ariadne as a ticket-centered local Agent Workbench. The target is a local API control plane that reuses the existing CLI/daemon/orchestrator capabilities, exposes typed agent actions to the React workbench, and keeps `fake-codex` and snapshot sync as offline fallback only. The review uses Multica's issue-agent-runtime model as the product benchmark and `agentic-coding` conventions as the architecture review lens: FSD for frontend, DDD layered boundaries for backend.

**Tech Stack:** Python 3.11, Typer, Pydantic v2, JSON/JSONL store, local daemon/runtime, Codex CLI, Claude Code CLI, DeepSeek, lark-cli, gh CLI, React/Vite/TypeScript.

---

## Review Scope

This is a review plan, not an implementation plan for the API server. The output of this plan is a written review report with concrete gaps, recommended implementation sequence, and acceptance criteria for the next development goal.

The review target is:

```text
CLI-driven agent loop
  -> local API-driven agent control plane
  -> frontend can assign, run, observe, and recover agent team work
```

The review must answer:

1. Can Ariadne currently let users dispatch agent teams from the frontend?
2. What exact API control plane is missing?
3. What agent team semantics must match Multica before this is product-credible?
4. How should frontend code be reorganized using FSD before adding real mutations?
5. How should backend code be reorganized toward DDD-style domain/application/interfaces boundaries before adding HTTP?
6. Which safety concerns block API design, and which should be tracked but not executed in this review?

## Non-Scope

Do not implement frontend mutations in this review.

Do not add a server, FastAPI, Flask, WebSocket, SSE, or new runtime dependency in this review.

Do not refactor `cli.py`, `orchestrator.py`, `models.py`, `storage.py`, or `App.tsx` in this review.

Do not change security gates in this review. Security can be reviewed and listed as a constraint, but this plan does not execute those fixes.

Do not claim Ariadne has Multica-level maturity just because the CLI path works.

Do not use `fake-codex`, `dry-run`, or `demo full` as evidence for frontend agent team dispatch.

## Reference Material

Local Ariadne files:

- `README.md`
- `docs/ops/2026-06-17-2043-ARIADNE_PRODUCTION_AGENT_WORKBENCH_ROADMAP.md`
- `docs/superpowers/plans/2026-06-17-2043-ariadne-production-agent-workbench-execution-plan.md`
- `docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md`
- `docs/architecture/ARIADNE_V1_RUNTIME_FLOW.md`
- `docs/architecture/multica_architecture_digest.md`
- `docs/architecture/ariadne_multica_gap_report.md`
- `ariadne_ltb/models.py`
- `ariadne_ltb/team.py`
- `ariadne_ltb/daemon.py`
- `ariadne_ltb/orchestrator.py`
- `ariadne_ltb/cli.py`
- `ariadne_ltb/storage.py`
- `ariadne_ltb/execution.py`
- `ariadne_ltb/board_server.py`
- `frontend/ariadne-workbench/README.md`
- `frontend/ariadne-workbench/src/App.tsx`
- `frontend/ariadne-workbench/src/data.ts`
- `frontend/ariadne-workbench/src/types.ts`
- `frontend/ariadne-workbench/scripts/sync-local-data.mjs`

External reference docs:

- `https://github.com/stvlynn/agentic-coding/blob/main/docs/frontend/README.md`
- `https://raw.githubusercontent.com/stvlynn/agentic-coding/main/docs/frontend/layers.md`
- `https://raw.githubusercontent.com/stvlynn/agentic-coding/main/docs/frontend/import-rules.md`
- `https://github.com/stvlynn/agentic-coding/blob/main/docs/backend/README.md`
- `https://raw.githubusercontent.com/stvlynn/agentic-coding/main/docs/backend/application.md`
- `https://raw.githubusercontent.com/stvlynn/agentic-coding/main/docs/backend/interfaces.md`

Reference principles to apply:

- FSD frontend layers: `app -> pages -> widgets -> features -> entities -> shared`.
- FSD pages stay thin; feature slices own user scenarios; entities own domain data and pure rules; shared owns primitives.
- DDD backend layering: domain owns business rules; application owns use cases and DTOs; interfaces adapt HTTP/CLI/events.
- CLI and HTTP must call the same application services. Do not create a second agent scheduling path for the frontend.

## Review Output File

Create this review report:

```text
docs/reviews/2026-06-18-ariadne-agent-control-plane-review.md
```

The report must use this exact section structure:

```markdown
# Ariadne Agent Control Plane Review

## Executive Conclusion

## Current State Evidence

## Multica Alignment Review

## Agent Team Dispatch Review

## Local API Control Plane Gap

## Frontend FSD Review

## Backend DDD Boundary Review

## Code Quality And Maintainability Review

## Security Observations Not Executed In This Review

## P0 Implementation Backlog

## P1 Implementation Backlog

## P2 Implementation Backlog

## Acceptance Criteria For The Next Development Goal

## Verification Commands
```

## File Structure For Future Implementation

The review should recommend, not create, this implementation structure:

```text
ariadne_ltb/domain/
  tickets.py
  assignments.py
  agents.py
  runtime.py

ariadne_ltb/application/
  workbench_projection.py
  route_ticket.py
  assign_ticket.py
  run_assignment.py
  stream_run_events.py
  record_ticket_comment.py

ariadne_ltb/interfaces/
  cli/
  http/

frontend/ariadne-workbench/src/
  app/
  pages/workbench/
  widgets/ticket-detail/
  widgets/runtime-panel/
  widgets/agent-dock/
  features/assign-ticket/
  features/run-agent/
  features/route-ticket/
  features/watch-run-events/
  entities/ticket/
  entities/assignment/
  entities/runtime/
  shared/api/
  shared/ui/
```

The review must explicitly state that this structure is a recommended implementation target, not something already present.

---

### Task 1: Establish Current-State Baseline

**Files:**
- Read: `README.md`
- Read: `docs/ops/2026-06-17-2043-ARIADNE_PRODUCTION_AGENT_WORKBENCH_ROADMAP.md`
- Read: `docs/superpowers/plans/2026-06-17-2043-ariadne-production-agent-workbench-execution-plan.md`
- Read: `frontend/ariadne-workbench/README.md`
- Read: `frontend/ariadne-workbench/src/data.ts`
- Read: `frontend/ariadne-workbench/src/App.tsx`
- Create: `docs/reviews/2026-06-18-ariadne-agent-control-plane-review.md`

- [ ] **Step 1: Confirm repository state**

Run:

```bash
pwd
git status --short --branch
git log --oneline -1
```

Expected:

```text
/Users/martinlos/code/Ariadne.worktrees/ariadne-core-orchestration-backends-3
## main tracking origin/main
eefbf6b fix: make production backend smoke repeatable
```

If the branch or commit differs, record the actual branch and commit under `## Current State Evidence`.

- [ ] **Step 2: Confirm product acceptance snapshot**

Run:

```bash
python3.11 -m ariadne_ltb.cli doctor product --require-acceptance-ready
```

Expected evidence to record:

```text
Production acceptance: ready
real_codex_execution_evidence: ready
real_claude_execution_evidence: ready
real_feishu_write_evidence: ready
real_github_write_evidence: ready
Run gates: action_required
```

Interpretation to write in the report:

```text
Production acceptance proves real integration evidence exists. It does not prove the frontend can dispatch agent teams.
```

- [ ] **Step 3: Confirm current frontend is read-only**

Read:

```bash
rg -n "read-only|does not mutate|web_data|fetch\\(|sync:data|does not call" README.md frontend/ariadne-workbench/README.md frontend/ariadne-workbench/src/data.ts frontend/ariadne-workbench/src/App.tsx
```

Expected evidence:

```text
README.md says the workbench is read-only.
frontend README says it does not depend on backend APIs and does not mutate Ariadne core domain models.
data.ts fetches /web_data/workbench.json.
Agent Dock sendMessage only updates local React state.
```

- [ ] **Step 4: Start the review report**

Create `docs/reviews/2026-06-18-ariadne-agent-control-plane-review.md` with:

```markdown
# Ariadne Agent Control Plane Review

## Executive Conclusion

Ariadne has a working local agent execution kernel, but it does not yet have a frontend-operable agent control plane. The current workbench reads generated snapshots; it cannot route tickets, assign agents, start daemon work, stream run progress, or recover blockers from the browser. The next product milestone is to convert the CLI-driven loop into a local API-driven control plane and connect the frontend to typed actions.

## Current State Evidence

- Current branch:
- Current commit:
- Product acceptance:
- Frontend mode:
- Runtime dispatch path:
```

- [ ] **Step 5: Commit the review report skeleton**

Run:

```bash
git add docs/reviews/2026-06-18-ariadne-agent-control-plane-review.md
git commit -m "docs: start agent control plane review"
```

Expected:

```text
[main <sha>] docs: start agent control plane review
```

If the review is being written on a feature branch, replace `main` with the actual branch name in the report.

---

### Task 2: Multica Alignment Review

**Files:**
- Read: `docs/architecture/multica_architecture_digest.md`
- Read: `docs/architecture/ariadne_multica_gap_report.md`
- Read: `docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md`
- Read: `ariadne_ltb/models.py`
- Read: `ariadne_ltb/team.py`
- Read: `ariadne_ltb/daemon.py`
- Modify: `docs/reviews/2026-06-18-ariadne-agent-control-plane-review.md`

- [ ] **Step 1: Extract the Multica benchmark capabilities**

Record whether Ariadne has each capability:

```markdown
| Capability | Ariadne Status | Evidence | Gap |
|---|---|---|---|
| Issue/Ticket center | Present | `BuildTicket` in `models.py` | Needs frontend control |
| Agent profile | Present | `AgentProfile` in `models.py` | Needs UI management |
| Assignment lifecycle | Present | `TicketAssignment` in `models.py` | Needs frontend run controls |
| Runtime/daemon | Present local-only | `LocalDaemonWorker` in `daemon.py` | Needs API/event stream |
| Progress/comments | Present | comments + runtime journal | Needs live frontend stream |
| Board/workbench | Present read-only | React snapshot workbench | Needs mutations |
| Skills/MCP/env/runtime config | Partial | skills + runtime capability | Needs agent configuration UI |
```

- [ ] **Step 2: Write the Multica alignment conclusion**

Add this conclusion to the report:

```markdown
## Multica Alignment Review

Ariadne matches Multica's architecture idea at the local kernel level: ticket, agent profile, assignment, daemon/runtime, progress, review, memory, board, and evidence exist. Ariadne does not yet match Multica at the product control-plane level because the frontend cannot issue typed runtime actions and cannot observe live assignment progress from an API or event stream.
```

- [ ] **Step 3: Identify the non-negotiable Multica parity gap**

Add this exact gap statement:

```markdown
The non-negotiable gap is frontend dispatch. If a user cannot select a ticket, select an agent/runtime, click assign/run, and watch the assignment lifecycle progress, Ariadne is not yet comparable to Multica for agent-team operation.
```

- [ ] **Step 4: Commit Multica alignment section**

Run:

```bash
git add docs/reviews/2026-06-18-ariadne-agent-control-plane-review.md
git commit -m "docs: review multica alignment gap"
```

---

### Task 3: Agent Team Dispatch Review

**Files:**
- Read: `ariadne_ltb/models.py`
- Read: `ariadne_ltb/storage.py`
- Read: `ariadne_ltb/team.py`
- Read: `ariadne_ltb/daemon.py`
- Read: `ariadne_ltb/orchestrator.py`
- Read: `ariadne_ltb/execution.py`
- Read: `ariadne_ltb/llm_agents.py`
- Modify: `docs/reviews/2026-06-18-ariadne-agent-control-plane-review.md`

- [ ] **Step 1: Map the current dispatch path**

Use this diagram in the report:

```text
Ticket
  -> route_ticket_to_build_team(ticket, team_profile)
  -> RouteDecision
  -> TicketAssignment queued
  -> LocalDaemonWorker.run_once(assignment_id)
  -> TicketRunOrchestrator.run_ticket(ticket_id_or_key, backend_name)
  -> backend execution
  -> review
  -> memory
  -> next tickets
  -> board/evidence
```

- [ ] **Step 2: Classify real vs fallback agent capabilities**

Add this table:

```markdown
| Capability | Current Status | Product Interpretation |
|---|---|---|
| DeepSeek Build Lead / Knowledge / Memory roles | Real when key is present | Product capability |
| CodexBackend | Real when env gate and confirmation are present | Product coding runtime |
| ClaudeCodeBackend | Real when env gate and confirmation are present | Product coding runtime |
| Feishu write | Real when lark-cli, env gate, and confirmation are present | Product integration |
| GitHub issue/PR/comment/status | Real through gh with confirmation | Product integration |
| FakeCodexBackend | Deterministic fixture | Test/offline fallback only |
| DryRunBackend | No-write preview | Preview/fallback only |
| `agents.py` deterministic pipeline | Legacy fixed pipeline | Not product agent team control |
```

- [ ] **Step 3: Identify frontend-dispatch blockers**

Write these blockers:

```markdown
1. There is no local HTTP/API adapter for `route_ticket_to_build_team`, `create_assignment`, or `LocalDaemonWorker.run_once`.
2. There is no event stream for assignment lifecycle or run messages.
3. The frontend cannot choose a runtime and submit an assignment through a typed action.
4. The frontend cannot distinguish production backends from offline fallback choices through a server-authoritative capability contract.
5. The default missing `target_repo_path` behavior can fall back to the demo target; an API must require a registered target project for production actions.
```

- [ ] **Step 4: Write required product behavior**

Add:

```markdown
The minimum acceptable product behavior is: from the workbench, a user selects a ticket, selects Codex or Claude Code, clicks assign, sees the assignment queued, clicks run or lets the daemon claim it, watches progress events, sees diff/tests/review/memory/next tickets, and can open the blocker/recovery path when the run fails.
```

- [ ] **Step 5: Commit agent dispatch review**

Run:

```bash
git add docs/reviews/2026-06-18-ariadne-agent-control-plane-review.md
git commit -m "docs: review agent team dispatch"
```

---

### Task 4: Local API Control Plane Review

**Files:**
- Read: `ariadne_ltb/cli.py`
- Read: `ariadne_ltb/daemon.py`
- Read: `ariadne_ltb/orchestrator.py`
- Read: `ariadne_ltb/storage.py`
- Read: `ariadne_ltb/board_server.py`
- Modify: `docs/reviews/2026-06-18-ariadne-agent-control-plane-review.md`

- [ ] **Step 1: Record why CLI is not enough**

Add:

```markdown
CLI commands prove the use cases exist, but they are not a frontend control plane. A browser needs typed request/response contracts, idempotent mutation endpoints, status polling or streaming, and server-owned validation. Shelling out to `ari` from the frontend is not acceptable.
```

- [ ] **Step 2: Define the minimum API surface**

Add this endpoint table:

```markdown
| Method | Path | Purpose | Reuses Existing Capability |
|---|---|---|---|
| GET | `/api/workbench` | Return versioned workbench snapshot | replace `sync-local-data.mjs` as primary path |
| GET | `/api/tickets` | List tickets with lifecycle state | `AriadneStore.list_tickets` |
| GET | `/api/tickets/{ticket_id}` | Ticket detail projection | store + artifacts + integrations |
| POST | `/api/tickets/{ticket_id}/route` | Route ticket to build team | `route_ticket_to_build_team` |
| POST | `/api/tickets/{ticket_id}/assign` | Create typed assignment | `AriadneStore.create_assignment` |
| POST | `/api/assignments/{assignment_id}/run` | Run a specific assignment | `LocalDaemonWorker.run_once(assignment_id=assignment_id)` |
| GET | `/api/assignments/{assignment_id}/events` | Return assignment events | runtime journal + run messages |
| GET | `/api/runtime/status` | Return daemon heartbeat and capabilities | heartbeat + runtime capability snapshot |
| POST | `/api/tickets/{ticket_id}/comments` | Add human comment | store comments |
| POST | `/api/inbox/{item_id}/recover` | Dispatch repair/recovery | inbox recovery flow |
```

- [ ] **Step 3: Define request DTOs**

Add:

```markdown
### Required API DTOs

`AssignTicketRequest`:

```json
{
  "agent_id": "codex",
  "backend_name": "codex",
  "runtime_profile": "production",
  "target_project_id": "local-default",
  "idempotency_key": "uuid"
}
```

`RunAssignmentRequest`:

```json
{
  "confirm_execution": true,
  "confirmation_token": "server-issued-token",
  "timeout_seconds": 240,
  "idempotency_key": "uuid"
}
```

`RouteTicketRequest`:

```json
{
  "team_id": "build-team",
  "preferred_agent_id": "codex",
  "runtime_profile": "production"
}
```
```

- [ ] **Step 4: Define API design rules**

Add:

```markdown
### API Design Rules

1. The frontend must never send raw shell commands, command templates, or arbitrary filesystem paths.
2. API handlers must call application services; they must not duplicate CLI business logic.
3. CLI and HTTP must share the same command/use-case layer.
4. Every mutation must have an idempotency key.
5. Every mutation must write a comment, runtime event, or inbox item that appears in the workbench.
6. `sync-local-data.mjs` remains offline fallback, not the primary product data path.
```

- [ ] **Step 5: Commit API control plane review**

Run:

```bash
git add docs/reviews/2026-06-18-ariadne-agent-control-plane-review.md
git commit -m "docs: review local api control plane"
```

---

### Task 5: Frontend FSD Review

**Files:**
- Read: `frontend/ariadne-workbench/src/App.tsx`
- Read: `frontend/ariadne-workbench/src/data.ts`
- Read: `frontend/ariadne-workbench/src/types.ts`
- Read: `frontend/ariadne-workbench/src/styles.css`
- Read: `frontend/ariadne-workbench/scripts/sync-local-data.mjs`
- Modify: `docs/reviews/2026-06-18-ariadne-agent-control-plane-review.md`

- [ ] **Step 1: Record current frontend architecture**

Add:

```markdown
## Frontend FSD Review

Current frontend architecture is not FSD. `App.tsx` contains routing, pages, widgets, panels, local message behavior, and helpers in one file. `data.ts` mixes fixture data and production loader fallback. `sync-local-data.mjs` reads the `.ariadne` store directly and performs a custom projection into frontend state.
```

- [ ] **Step 2: Define target FSD structure**

Add:

```text
frontend/ariadne-workbench/src/
  app/
    App.tsx
    providers/
  pages/
    workbench/
    tickets/
    agents/
    inbox/
  widgets/
    sidebar/
    ticket-detail/
    runtime-panel/
    agent-dock/
    evidence-panel/
  features/
    assign-ticket/
    run-assignment/
    route-ticket/
    watch-run-events/
    add-ticket-comment/
    recover-inbox-item/
  entities/
    ticket/
    assignment/
    agent/
    runtime/
    evidence/
  shared/
    api/
    ui/
    lib/
```

- [ ] **Step 3: Classify current UI actions**

Use this table:

```markdown
| UI Area | Current Behavior | Review Verdict |
|---|---|---|
| Ticket list selection | Real local UI state | Keep |
| Ticket detail evidence | Real snapshot display | Keep, move to widget |
| Agent Dock send | Local React message only | Fake interaction; must not imply runtime action |
| Runtime picker | Local UI state | Needs API-backed runtime capability |
| Import/Generate buttons | No backend mutation | Disable or wire to API |
| Refresh snapshot | No live API | Replace with `GET /api/workbench` |
```

- [ ] **Step 4: Define first frontend API-backed features**

Add:

```markdown
The first API-backed frontend features should be:

1. `features/assign-ticket`: assign selected ticket to selected agent/runtime.
2. `features/run-assignment`: run a specific queued assignment.
3. `features/watch-run-events`: poll or stream assignment events.
4. `features/add-ticket-comment`: write human comments into ticket history.
5. `features/recover-inbox-item`: trigger repair/recovery for a blocker.
```

- [ ] **Step 5: Commit frontend FSD review**

Run:

```bash
git add docs/reviews/2026-06-18-ariadne-agent-control-plane-review.md
git commit -m "docs: review frontend fsd control plane"
```

---

### Task 6: Backend DDD Boundary Review

**Files:**
- Read: `ariadne_ltb/cli.py`
- Read: `ariadne_ltb/orchestrator.py`
- Read: `ariadne_ltb/storage.py`
- Read: `ariadne_ltb/models.py`
- Read: `ariadne_ltb/team.py`
- Read: `ariadne_ltb/daemon.py`
- Modify: `docs/reviews/2026-06-18-ariadne-agent-control-plane-review.md`

- [ ] **Step 1: Record current backend boundary problem**

Add:

```markdown
## Backend DDD Boundary Review

Current backend organization is functional but not ready for a second interface layer. `cli.py` is a large interface file that also contains business decisions and output formatting. `AriadneStore` owns directory layout plus many repository responsibilities. `TicketRunOrchestrator.run_ticket` coordinates the entire workflow in one long method. Before adding HTTP, Ariadne needs application services that both CLI and HTTP can call.
```

- [ ] **Step 2: Define target backend layers**

Add:

```markdown
### Recommended Backend Layers

`domain`:
- Ticket lifecycle rules.
- Assignment lifecycle rules.
- Agent/team routing decisions.
- Runtime capability concepts.

`application`:
- `AssignTicketService`
- `RouteTicketService`
- `RunAssignmentService`
- `WorkbenchProjectionService`
- `RunEventsQueryService`
- `AddTicketCommentService`
- `RecoverInboxItemService`

`infrastructure`:
- `AriadneStore`
- JSON/JSONL persistence.
- Codex/Claude/DeepSeek/Feishu/GitHub adapters.

`interfaces`:
- Typer CLI handlers.
- Local HTTP handlers.
- Static board/workbench adapters.
```

- [ ] **Step 3: Define service signatures to review**

Add this review-only interface sketch to clarify the target service boundary:

```python
class AssignTicketService:
    def execute(self, command: AssignTicketCommand) -> AssignmentDto:
        raise NotImplementedError("Review target: assign one ticket to an agent role")

class RunAssignmentService:
    def execute(self, command: RunAssignmentCommand) -> AssignmentRunDto:
        raise NotImplementedError("Review target: run one existing assignment")

class WorkbenchProjectionService:
    def get_snapshot(self) -> WorkbenchSnapshotDto:
        raise NotImplementedError("Review target: return the current workbench projection")

class RunEventsQueryService:
    def list_events(self, assignment_id: str, since: str | None = None) -> list[RunEventDto]:
        raise NotImplementedError("Review target: list progress events for one assignment")
```

- [ ] **Step 4: Identify files that should not grow further**

Add:

```markdown
Files that should not grow further without extraction:

- `ariadne_ltb/cli.py`
- `ariadne_ltb/orchestrator.py`
- `ariadne_ltb/models.py`
- `ariadne_ltb/storage.py`
- `ariadne_ltb/backlog.py`
- `frontend/ariadne-workbench/src/App.tsx`
- `frontend/ariadne-workbench/src/data.ts`
- `frontend/ariadne-workbench/scripts/sync-local-data.mjs`
```

- [ ] **Step 5: Commit backend DDD review**

Run:

```bash
git add docs/reviews/2026-06-18-ariadne-agent-control-plane-review.md
git commit -m "docs: review backend ddd boundaries"
```

---

### Task 7: Security Observations Without Execution

**Files:**
- Read: `ariadne_ltb/execution.py`
- Read: `ariadne_ltb/permissions.py`
- Read: `ariadne_ltb/feishu.py`
- Read: `ariadne_ltb/github_integration.py`
- Read: `ariadne_ltb/secret_safety.py`
- Modify: `docs/reviews/2026-06-18-ariadne-agent-control-plane-review.md`

- [ ] **Step 1: Add security observations section**

Add:

```markdown
## Security Observations Not Executed In This Review

Security is reviewed here only as a design constraint. This review does not execute security hardening tasks.

Observations:

1. Codex and Claude Code have external execution gates.
2. Feishu write has an env gate plus confirmation.
3. GitHub writes currently rely on confirmation and should gain an env gate before frontend-triggered writes.
4. Shell backend should not be exposed to frontend/API actions.
5. Browser actions must be typed server actions; they must not accept raw shell commands, command templates, or arbitrary paths.
6. `.ariadne` artifacts and handoffs must not be shipped in frontend bundles or remote logs.
```

- [ ] **Step 2: Add deferred security backlog**

Add:

```markdown
Deferred security backlog:

- Add `GITHUB_ENABLE_WRITE=1` gate for GitHub mutations.
- Add release-bound artifact redaction scan over `.ariadne` evidence selected for export.
- Ensure API actions require registered target projects, not arbitrary absolute paths.
- Ensure handoff and stdout/stderr content is redacted before frontend streaming.
- Keep `shell` backend unavailable from the web control plane.
```

- [ ] **Step 3: Commit security observations**

Run:

```bash
git add docs/reviews/2026-06-18-ariadne-agent-control-plane-review.md
git commit -m "docs: record control plane security observations"
```

---

### Task 8: Produce Implementation Backlog And Acceptance Criteria

**Files:**
- Modify: `docs/reviews/2026-06-18-ariadne-agent-control-plane-review.md`

- [ ] **Step 1: Write P0 implementation backlog**

Add:

```markdown
## P0 Implementation Backlog

1. Create versioned `WorkbenchSnapshotDto` in Python.
2. Create `WorkbenchProjectionService` that reads AriadneStore and returns the DTO.
3. Add local API server bound to `127.0.0.1`.
4. Add `GET /api/workbench`.
5. Add `POST /api/tickets/{ticket_id}/assign`.
6. Add `POST /api/assignments/{assignment_id}/run`.
7. Add `GET /api/assignments/{assignment_id}/events`.
8. Update frontend data adapter to prefer API and keep snapshot JSON as offline fallback.
9. Wire first real frontend actions: assign ticket, run assignment, watch progress.
10. Add tests proving frontend-triggered actions use existing store/daemon/orchestrator path.
```

- [ ] **Step 2: Write P1 implementation backlog**

Add:

```markdown
## P1 Implementation Backlog

1. Add route-to-build-team API endpoint.
2. Add ticket comment API endpoint.
3. Add inbox recovery API endpoint.
4. Split frontend into FSD slices for tickets, assignments, runtime, and agent actions.
5. Split CLI command handlers into interface modules that call application services.
6. Add API contract golden tests.
7. Add event stream fallback from SSE to polling.
```

- [ ] **Step 3: Write P2 implementation backlog**

Add:

```markdown
## P2 Implementation Backlog

1. Split `App.tsx` into pages/widgets/features/entities/shared.
2. Split `cli.py` into thin command modules.
3. Split `models.py` by domain area.
4. Split `AriadneStore` into repositories or store facets.
5. Add deeper runtime configuration UI for agent profiles, skills, model selection, and environment settings.
6. Add cancellation and retry controls from the frontend.
```

- [ ] **Step 4: Write acceptance criteria**

Add:

```markdown
## Acceptance Criteria For The Next Development Goal

The next development goal is complete only when:

1. The workbench can load data from a local API, not only from `web_data/workbench.json`.
2. A user can select a ticket and assign it to Codex or Claude Code from the frontend.
3. A user can run a queued assignment from the frontend.
4. The frontend shows assignment lifecycle progress from API events or polling.
5. The run uses `LocalDaemonWorker` and `TicketRunOrchestrator`; no second execution path exists.
6. The frontend shows diff, tests, review verdict, memory, next tickets, and blocker status after the run.
7. Offline snapshot mode remains available but is labelled fallback.
8. Deterministic tests do not require real Codex, Claude, DeepSeek, Feishu, GitHub, or network.
9. Frontend typecheck and build pass.
10. Python pytest and ruff pass.
```

- [ ] **Step 5: Write verification commands**

Add:

```markdown
## Verification Commands

```bash
python3.11 -m pytest
python3.11 -m ruff check .
python3.11 -m ariadne_ltb.cli doctor product --require-acceptance-ready
scripts/verify_workbench.sh
scripts/verify_v1.sh
```

Frontend implementation follow-up must also run:

```bash
cd frontend/ariadne-workbench
npm run typecheck
npm run build
```
```

- [ ] **Step 6: Commit backlog and acceptance criteria**

Run:

```bash
git add docs/reviews/2026-06-18-ariadne-agent-control-plane-review.md
git commit -m "docs: define control plane implementation backlog"
```

---

### Task 9: Final Self-Review

**Files:**
- Read: `docs/reviews/2026-06-18-ariadne-agent-control-plane-review.md`

- [ ] **Step 1: Check report coverage**

Run:

```bash
rg -n "Executive Conclusion|Multica Alignment|Agent Team Dispatch|Local API Control Plane|Frontend FSD|Backend DDD|Security Observations|P0 Implementation Backlog|Acceptance Criteria" docs/reviews/2026-06-18-ariadne-agent-control-plane-review.md
```

Expected:

```text
Each required section appears exactly once.
```

- [ ] **Step 2: Check for forbidden vague placeholders**

Run:

```bash
rg -n "TBD|TODO|implement later|similar to|as appropriate|etc\\.|and so on" docs/reviews/2026-06-18-ariadne-agent-control-plane-review.md
```

Expected:

```text
No matches.
```

- [ ] **Step 3: Check git state**

Run:

```bash
git status --short --branch
```

Expected:

```text
No uncommitted changes.
```

- [ ] **Step 4: Push review branch**

If the review was committed directly on `main`, run:

```bash
git push origin main
```

If the review was committed on a feature branch, run:

```bash
git push -u origin <branch-name>
```

- [ ] **Step 5: Final answer**

Report:

```text
1. Review report path.
2. Main conclusion.
3. The next implementation goal.
4. Commands run.
5. Whether any security item was reviewed but intentionally not executed.
```

## Plan Self-Review

Spec coverage:

- The plan reviews the gap between read-only frontend and frontend-triggered agent team dispatch.
- The plan aligns the agent review with Multica's issue-agent-runtime model.
- The plan uses `agentic-coding` frontend FSD and backend DDD conventions as review lenses.
- The plan keeps security gate work as observations only, not execution.
- The plan defines a concrete next goal: local API control plane plus frontend actions.

Placeholder scan:

- This plan avoids `TBD`, `TODO`, `implement later`, and unspecified steps.
- Every task has exact files, exact commands, and concrete output text.

Type and naming consistency:

- The target API names are consistently `WorkbenchSnapshotDto`, `AssignTicketRequest`, `RunAssignmentRequest`, and `RouteTicketRequest`.
- The target service names are consistently `WorkbenchProjectionService`, `AssignTicketService`, `RunAssignmentService`, and `RunEventsQueryService`.
