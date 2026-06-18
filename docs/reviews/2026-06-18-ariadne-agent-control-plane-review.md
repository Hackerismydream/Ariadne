# Ariadne Agent Control Plane Review

## Executive Conclusion

Verdict: **partial**.

Ariadne has a real local agent execution kernel, but it is not yet a Multica-like frontend-operable agent control plane.

The kernel is credible: tickets, agent profiles, build teams, assignments, daemon claiming, Codex/Claude execution backends, DeepSeek LLM roles, runtime events, comments, review, memory, next tickets, board, and evidence all exist. The missing product layer is the browser control plane. Today the frontend reads a generated snapshot; it cannot route a ticket, assign an agent team, run an assignment, observe live lifecycle events, comment into the ticket loop, or recover a blocker through typed API actions.

The next product milestone is:

```text
CLI-driven agent loop
  -> local API-driven agent control plane
  -> frontend can assign, run, observe, and recover agent team work
```

Do not treat `fake-codex`, `dry-run`, `demo full`, static board serving, or `/web_data/workbench.json` as product-path evidence. They remain useful as regression and offline fallback paths only.

## Current State Evidence

- Current repository path: `/Users/martinlos/code/Ariadne.worktrees/ariadne-core-orchestration-backends-3`.
- Current branch state during review: `main` tracking `origin/main`.
- Current commit during review: `ea43889 docs: plan agent control plane review`.
- Product doctor command passed production acceptance:
  - `Product readiness: action_required`
  - `Production acceptance: ready`
  - `Run gates: action_required`
  - `deepseek_llm: ready`
  - `codex_backend: ready`
  - `claude_code_backend: ready`
  - `real_codex_execution_evidence: ready`
  - `real_claude_execution_evidence: ready`
  - `real_feishu_write_evidence: ready`
  - `real_github_write_evidence: ready`
- This proves real integration evidence exists. It does not prove frontend dispatch exists.
- `README.md:474` says the local workbench frontend is read-only.
- `README.md:475` says it does not call Multica APIs.
- `README.md:476` says it does not mutate Ariadne state.
- `frontend/ariadne-workbench/README.md:62` says the frontend does not mutate Ariadne core domain models.
- `frontend/ariadne-workbench/src/data.ts:482` defines `loadWorkbenchData`.
- `frontend/ariadne-workbench/src/data.ts:484` only fetches `/web_data/workbench.json`.
- `frontend/ariadne-workbench/src/App.tsx:1215` defines `sendMessage`.
- `frontend/ariadne-workbench/src/App.tsx:1218` only updates local React message state.

Cross-review coverage:

| Area | Reviewer pair | Verdict | Shared conclusion |
|---|---|---|---|
| Multica alignment and dispatch | A + B | partial | Kernel exists; browser dispatch does not. |
| API control plane and backend boundaries | C + D | partial | Existing CLI/daemon/orchestrator can be reused, but need application services and tight API contracts. |
| Frontend FSD, product fit, safety observations | E + F | partial | Frontend is a static snapshot viewer; P0 is typed API actions before cosmetic FSD splitting. |

## Multica Alignment Review

Ariadne matches Multica's architecture idea at the local kernel level:

| Capability | Ariadne Status | Evidence | Gap |
|---|---|---|---|
| Issue/Ticket center | Present | `BuildTicket` in `ariadne_ltb/models.py:640` | Needs frontend operation. |
| Agent profile | Present | `AgentProfile` in `ariadne_ltb/models.py:449` | Needs UI management and capability-backed actions. |
| Build team | Present | `BuildTeam` in `ariadne_ltb/models.py:464` | Needs frontend route/assign workflow. |
| Assignment lifecycle | Present | `TicketAssignment` in `ariadne_ltb/models.py:482` | Needs API run controls and event projection. |
| Agent run lifecycle | Present | `AgentRun` in `ariadne_ltb/models.py:755` | Needs live run visibility. |
| Runtime/daemon | Present local-only | `LocalDaemonWorker.run_once` in `ariadne_ltb/daemon.py:43` | Needs local API/event stream. |
| Route decision | Present | `route_ticket_to_build_team` in `ariadne_ltb/team.py:35` | Needs browser-triggered routing. |
| Runtime capability | Present | `RuntimeCapability` in `ariadne_ltb/models.py:970` | Needs redacted server-authoritative API contract. |
| Board/workbench | Present read-only | React snapshot workbench | Needs mutations and live refresh. |

The non-negotiable Multica parity gap is frontend dispatch. If a user cannot select a ticket, select an agent/runtime, click assign/run, and watch the assignment lifecycle progress, Ariadne is not comparable to Multica for agent-team operation.

Multica's product essence is not only "many agents". It is issue-centered work management: issue, assignment/task, runtime claim, visible progress, blocker, review, and board. Ariadne has many of these objects locally, but the product surface is still CLI-first and snapshot-first.

## Agent Team Dispatch Review

Current dispatch path:

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

Evidence:

- `ariadne_ltb/team.py:35` defines `route_ticket_to_build_team`.
- `ariadne_ltb/team.py:53` falls back to `ensure_demo_target_project` when `target_repo_path` is missing.
- `ariadne_ltb/team.py:117` creates a `TicketAssignment`.
- `ariadne_ltb/storage.py:271` creates assignments and writes related side effects.
- `ariadne_ltb/storage.py:368` claims assignments.
- `ariadne_ltb/daemon.py:43` can run one assignment.
- `ariadne_ltb/daemon.py:113` calls `TicketRunOrchestrator`.
- `ariadne_ltb/orchestrator.py:109` defines the full ticket loop.
- `ariadne_ltb/orchestrator.py:213` also falls back to demo target when `target_repo_path` is omitted.

Capability classification:

| Capability | Current Status | Product Interpretation |
|---|---|---|
| DeepSeek Build Lead / Knowledge / Reviewer / Memory roles | Real when key is present | Product capability. |
| CodexBackend | Real when env gate and confirmation are present | Product coding runtime. |
| ClaudeCodeBackend | Real when env gate and confirmation are present | Product coding runtime. |
| Feishu write | Real when lark-cli, env gate, and confirmation are present | Product integration. |
| GitHub issue/PR/comment/status | Real through `gh` with confirmation | Product integration. |
| FakeCodexBackend | Deterministic fixture | Test/offline fallback only. |
| DryRunBackend | No-write preview | Preview/fallback only. |
| `agents.py` deterministic pipeline | Legacy fixed pipeline | Not product agent team control. |

P0 dispatch blockers:

1. No local HTTP/API adapter exposes `route_ticket_to_build_team`, `AriadneStore.create_assignment`, or `LocalDaemonWorker.run_once`.
2. No frontend typed mutation exists for selecting ticket + runtime + agent/team and creating/running an assignment.
3. No event stream or polling contract exposes assignment lifecycle, run messages, runtime journal, heartbeat, blockers, and recovery state.
4. No server-authoritative capability contract tells the frontend which backends are production-capable versus fixture/fallback.
5. Production dispatch can still silently fall back to the demo target when `target_repo_path` is omitted. Frontend/API production actions must require a registered project resource.

Minimum acceptable product behavior:

```text
From the workbench, a user selects a ticket, selects Codex or Claude Code,
clicks assign, sees the assignment queued, clicks run or lets the daemon claim it,
watches progress events, sees diff/tests/review/memory/next tickets,
and can open blocker/recovery when the run fails.
```

## Local API Control Plane Gap

CLI commands prove the use cases exist, but they are not a frontend control plane. A browser needs typed request/response contracts, idempotent mutation endpoints, status polling or streaming, and server-owned validation. Shelling out to `ari` from the frontend is not acceptable.

Required first API surface:

| Method | Path | Purpose | Reuses Existing Capability |
|---|---|---|---|
| GET | `/api/workbench` | Return versioned workbench snapshot | Replace `sync-local-data.mjs` as primary path. |
| GET | `/api/runtime/status` | Return daemon heartbeat and redacted capabilities | Heartbeat + runtime capability snapshot. |
| POST | `/api/tickets/{ticket_id}/assign` | Create typed assignment | `route_ticket_to_build_team` and `AriadneStore.create_assignment`, behind service boundary. |
| POST | `/api/assignments/{assignment_id}/run` | Run a specific assignment | `LocalDaemonWorker.run_once(assignment_id=assignment_id)`. |
| GET | `/api/assignments/{assignment_id}/events` | Return assignment events | Runtime journal + run messages + comments. |
| POST | `/api/tickets/{ticket_id}/comments` | Add human comment | Store comments. |

P1 API surface:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/tickets` | Ticket list projection. |
| GET | `/api/tickets/{ticket_id}` | Ticket detail projection. |
| POST | `/api/tickets/{ticket_id}/route` | Explicit route-to-build-team action. |
| POST | `/api/inbox/{item_id}/recover` | Dispatch repair/recovery. |

Required request contracts:

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
  "runtime_profile": "production",
  "target_project_id": "local-default",
  "idempotency_key": "uuid"
}
```

API design rules:

1. The frontend must never send raw shell commands, command templates, allowed path lists, arbitrary filesystem paths, handoff file paths, test commands, or raw stdout/stderr.
2. The frontend may send stable ids and constrained enums only: `ticket_id`, `assignment_id`, `agent_id`, `backend_name` from server capability list, `target_project_id`, `runtime_profile`, and `idempotency_key`.
3. API handlers must call application services; they must not duplicate CLI business logic.
4. CLI and HTTP must share the same command/use-case layer.
5. Every mutation must have an idempotency key.
6. Every mutation must write a comment, runtime event, inbox item, or assignment event that appears in the workbench.
7. `shell` must stay unavailable from web actions.
8. `sync-local-data.mjs` remains offline fallback, not the primary product data path.

## Frontend FSD Review

Verdict: **partial**.

The current frontend is a useful read-only workbench, not an AI Builder control plane. It presents tickets, runtime state, artifacts, and agent context, but its data source is static snapshot JSON and its Agent Dock only mutates local React state.

Evidence:

- `frontend/ariadne-workbench/src/App.tsx:99` owns app state, routing, page composition, widgets, panels, helpers, selected ticket, and selected runtime in one file.
- `frontend/ariadne-workbench/src/App.tsx:1017` runtime selection is local state.
- `frontend/ariadne-workbench/src/App.tsx:1215` Agent Dock `sendMessage` is local-only.
- `frontend/ariadne-workbench/src/data.ts:482` loads `WorkbenchData`.
- `frontend/ariadne-workbench/src/data.ts:484` fetches `/web_data/workbench.json`.
- `frontend/ariadne-workbench/src/types.ts:280` defines snapshot-shaped `WorkbenchData`, not action DTOs.
- `frontend/ariadne-workbench/scripts/sync-local-data.mjs:502` reads `.ariadne` and writes a generated snapshot.

FSD gaps:

- No `app/pages/widgets/features/entities/shared` structure exists.
- `App.tsx` mixes app shell, routing, pages, widgets, entity rendering, helpers, and feature-like state changes.
- `data.ts` mixes seed fixtures, snapshot loading, merge fallback, and data-source semantics.
- Feature boundaries are absent for `assign-ticket`, `run-assignment`, `watch-run-events`, `add-ticket-comment`, and `recover-inbox-item`.

P0 is not a cosmetic folder move. P0 is a typed API-backed action model. The first frontend slices should be:

```text
features/assign-ticket
features/run-assignment
features/watch-run-events
shared/api
entities/ticket
entities/assignment
entities/runtime
```

P1 should complete the broader FSD split:

```text
app/
pages/workbench/
widgets/ticket-detail/
widgets/runtime-panel/
widgets/agent-dock/
features/route-ticket/
features/add-ticket-comment/
features/recover-inbox-item/
entities/artifact/
shared/ui/
```

## Backend DDD Boundary Review

Verdict: **partial**.

The backend has domain concepts, but the application boundary is not clean enough for HTTP. CLI handlers still own meaningful use-case logic; `AriadneStore` mixes repository behavior with side effects; and `TicketRunOrchestrator.run_ticket` exposes too broad an operator-oriented parameter surface for a browser action.

Evidence:

- `ariadne_ltb/cli.py:88` through `ariadne_ltb/cli.py:132` define many Typer command groups as the current interface layer.
- `ariadne_ltb/cli.py:1254` through `ariadne_ltb/cli.py:1348` implement `ticket assign`, including team-vs-agent branching, runtime profile resolution, assignment creation, ticket status updates, and output formatting.
- `ariadne_ltb/cli.py:1576` through `ariadne_ltb/cli.py:1650` implement `ticket run`, exposing backend, target path, command override, confirmation, memory, runtime profile, and worktree options.
- `ariadne_ltb/storage.py:271` through `ariadne_ltb/storage.py:333` create assignments and also write comments, runtime events, and ticket metadata.
- `ariadne_ltb/orchestrator.py:109` defines a full workflow entry point, not a narrow application service.
- `ariadne_ltb/daemon.py:43` through `ariadne_ltb/daemon.py:128` provides the reusable assignment run kernel.

Recommended target layering:

```text
ariadne_ltb/domain/
  tickets.py
  assignments.py
  agents.py
  runtime.py

ariadne_ltb/application/
  workbench_projection.py
  runtime_status.py
  assign_ticket.py
  run_assignment.py
  stream_run_events.py
  record_ticket_comment.py
  target_project_registry.py

ariadne_ltb/interfaces/
  cli/
  http/
```

Required application services:

- `WorkbenchProjectionService`
- `RuntimeStatusService`
- `AssignTicketService`
- `RunAssignmentService`
- `RunEventsQueryService`
- `AddTicketCommentService`
- `TargetProjectRegistry`
- `MutationIdempotencyStore`
- `RuntimeCapabilityRedactor`

P1 services:

- `RouteTicketService`
- `RecoverInboxItemService`
- `SupervisorRunService`

CLI and HTTP must both call these services. Do not build a parallel HTTP-only execution path.

## Code Quality And Maintainability Review

The current codebase can support the next milestone, but large files and blurred boundaries will make a direct API bolt-on risky.

Observed file sizes:

| File | Lines |
|---|---:|
| `ariadne_ltb/cli.py` | 3113 |
| `ariadne_ltb/orchestrator.py` | 1557 |
| `ariadne_ltb/models.py` | 1345 |
| `ariadne_ltb/storage.py` | 1110 |
| `ariadne_ltb/board.py` | 1108 |
| `frontend/ariadne-workbench/src/App.tsx` | 1331 |
| `frontend/ariadne-workbench/src/data.ts` | 511 |
| `frontend/ariadne-workbench/scripts/sync-local-data.mjs` | 668 |

Risk:

- Adding HTTP directly to these files will create a second interface without a stable application boundary.
- Adding frontend mutations directly to `App.tsx` will increase coupling and make FSD migration harder.
- Reusing snapshot DTOs as action DTOs will leak display-only state into mutation contracts.

Recommendation:

1. Add application services first.
2. Add typed DTOs and golden contract tests.
3. Add a local HTTP interface over those services.
4. Add frontend API client and P0 feature slices.
5. Keep snapshot sync as offline fallback.

## Security Observations Not Executed In This Review

Security was reviewed as a design constraint only. No security fixes were executed in this review.

Record these constraints for the next implementation:

- Codex and Claude execution must remain gated by environment + confirmation.
- Feishu writes must remain gated by environment + confirmation.
- GitHub frontend-triggered writes should gain an explicit environment gate before browser actions are allowed.
- `shell` backend must not be exposed to the web control plane.
- The browser must not send raw shell commands, command templates, arbitrary filesystem paths, allowed path lists, handoff file paths, test commands, or raw stdout/stderr.
- Runtime capability DTOs for the browser must be redacted. CLI diagnostics may show more local detail than the web control plane.
- Frontend-visible execution output must redact secrets, provider failures, command templates, handoff paths, `.ariadne` artifact paths, and raw stdout/stderr by default.
- Production dispatch must require a registered `target_project_id`; it must not fall back to demo target.

## P0 Implementation Backlog

1. Add `ariadne_ltb/application/workbench_projection.py`.
   - Provide `WorkbenchProjectionService`.
   - Return `WorkbenchSnapshotDto`.
   - Keep `/web_data/workbench.json` as offline fallback only.

2. Add `ariadne_ltb/application/runtime_status.py`.
   - Provide `RuntimeStatusService`.
   - Return daemon heartbeat, queue counts, and redacted runtime capabilities.
   - Hide `shell` from web actions.

3. Add `ariadne_ltb/application/assign_ticket.py`.
   - Provide `AssignTicketService`.
   - Accept `AssignTicketCommand`.
   - Require `target_project_id`.
   - Validate backend against server capability list.
   - Persist idempotency key.
   - Reuse `route_ticket_to_build_team` / `AriadneStore.create_assignment` without exposing raw paths.

4. Add `ariadne_ltb/application/run_assignment.py`.
   - Provide `RunAssignmentService`.
   - Accept `RunAssignmentCommand`.
   - Run only an existing assignment by id.
   - Reuse `LocalDaemonWorker.run_once(assignment_id=assignment_id)`.
   - Do not accept backend/path/command override.

5. Add `ariadne_ltb/application/run_events.py`.
   - Provide `RunEventsQueryService`.
   - Merge assignment state, runtime events, run messages, comments, blocker state, and review verdict into a stable event timeline.
   - Support polling cursor with `since`.

6. Add `ariadne_ltb/application/comments.py`.
   - Provide `AddTicketCommentService`.
   - Write human comments through the same store path used by CLI.
   - Require idempotency key.

7. Add `ariadne_ltb/application/target_project_registry.py`.
   - Register and resolve project resources by id.
   - Prevent production UI actions from using demo target fallback.

8. Add local HTTP interface.
   - Recommended path: `ariadne_ltb/interfaces/http/`.
   - Expose:
     - `GET /api/workbench`
     - `GET /api/runtime/status`
     - `POST /api/tickets/{ticket_id}/assign`
     - `POST /api/assignments/{assignment_id}/run`
     - `GET /api/assignments/{assignment_id}/events`
     - `POST /api/tickets/{ticket_id}/comments`

9. Add frontend API client.
   - Recommended path: `frontend/ariadne-workbench/src/shared/api/`.
   - Prefer local API.
   - Use snapshot JSON only as clearly labeled offline fallback.

10. Add first frontend feature slices.
    - `features/assign-ticket`
    - `features/run-assignment`
    - `features/watch-run-events`
    - Wire them to existing workbench selection state.

11. Add tests proving frontend-triggered API actions reuse the same backend path.
    - Assign creates assignment through service/store.
    - Run calls daemon/orchestrator path.
    - Events expose lifecycle state.
    - Browser DTOs reject raw command/path/shell backend.

## P1 Implementation Backlog

1. Add `RouteTicketService` and `/api/tickets/{ticket_id}/route`.
2. Add `RecoverInboxItemService` and `/api/inbox/{item_id}/recover`.
3. Add route-to-team frontend feature.
4. Add blocker recovery frontend feature.
5. Add build team / agent profile management UI.
6. Merge runtime events, comments, run messages, review, memory, and next tickets into one assignment timeline.
7. Add API contract golden fixtures.
8. Split `App.tsx` into FSD layers.
9. Split CLI handlers into `ariadne_ltb/interfaces/cli/`.
10. Start thinning `AriadneStore` into smaller repository modules.

## P2 Implementation Backlog

1. Add SSE event streaming after polling endpoints are stable.
2. Add web-managed confirmation tokens/action leases.
3. Add richer runtime queue states such as waiting for local directory, waiting for gate, running, review failed, recovery pending.
4. Add frontend runtime capability admin view.
5. Add optional GitHub/Feishu action surfaces after explicit gates exist.
6. Add broader FSD cleanup for all pages/widgets/entities.
7. Decompose `TicketRunOrchestrator` phases into smaller reusable services.

## Acceptance Criteria For The Next Development Goal

The next development goal is accepted only if all of these are true:

1. A local API server exists and can be started locally.
2. `GET /api/workbench` returns a versioned DTO without requiring static snapshot sync.
3. `POST /api/tickets/{ticket_id}/assign` creates a real assignment using the shared application service.
4. `POST /api/assignments/{assignment_id}/run` runs that assignment through `LocalDaemonWorker` and `TicketRunOrchestrator`.
5. `GET /api/assignments/{assignment_id}/events` exposes a visible assignment timeline.
6. Frontend can assign and run a ticket from the browser against the local API.
7. Frontend shows progress/events without requiring a manual `npm run sync:data`.
8. Frontend can add at least one human comment through API.
9. Browser mutation requests cannot include raw shell command, command template, arbitrary path, or `shell` backend.
10. Production UI actions require a registered target project.
11. `fake-codex`, `dry-run`, `demo full`, and snapshot sync remain available only as fallback/regression paths.
12. Existing CLI product path remains working.
13. Tests prove CLI and HTTP share application services rather than duplicate execution logic.

## Verification Commands

Commands run for this review:

```bash
pwd
git status --short --branch
git log --oneline -1
python3.11 -m ariadne_ltb.cli doctor product --require-acceptance-ready
rg -n "read-only|does not mutate|web_data|fetch\\(|sync:data|does not call|sendMessage|setMessages" README.md frontend/ariadne-workbench/README.md frontend/ariadne-workbench/src/data.ts frontend/ariadne-workbench/src/App.tsx
rg -n "class (BuildTicket|TicketAssignment|AgentProfile|BuildTeam|RouteDecision|RuntimeCapability|AgentRun)|lifecycle_state|failure_reason" ariadne_ltb/models.py
rg -n "class LocalDaemonWorker|def run_once|def claim_next_assignment|runtime journal|journal|heartbeat|assignment" ariadne_ltb/daemon.py
rg -n "def route_ticket_to_build_team|class BuildTeam|AgentProfile|TicketAssignment|RouteDecision|create_assignment" ariadne_ltb/team.py ariadne_ltb/storage.py
wc -l ariadne_ltb/cli.py ariadne_ltb/orchestrator.py ariadne_ltb/models.py ariadne_ltb/storage.py ariadne_ltb/board.py frontend/ariadne-workbench/src/App.tsx frontend/ariadne-workbench/src/data.ts frontend/ariadne-workbench/src/types.ts frontend/ariadne-workbench/scripts/sync-local-data.mjs
```

Expected next-review checks:

```bash
rg -n "Executive Conclusion|Multica Alignment|Agent Team Dispatch|Local API Control Plane|Frontend FSD|Backend DDD|Security Observations|P0 Implementation Backlog|Acceptance Criteria" docs/reviews/2026-06-18-ariadne-agent-control-plane-review.md
git diff --check
```

Also run the plan's forbidden-placeholder scan against this report and confirm it returns no report-content matches.
