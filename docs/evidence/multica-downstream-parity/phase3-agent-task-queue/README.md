# Phase 3 Agent Task Queue Evidence

## Scope

Phase 3 implements the Multica-style Agent Task Queue surface for Ariadne:

- assigning a current BuildTicket from Issue Detail to a real `AgentDefinition`;
- projecting that assignment as an Agent task from `TicketAssignment`;
- showing task lifecycle fields in Agent Detail / Tasks;
- linking blocked tasks to Inbox when a blocker exists.

## Three Anchors

### 1. CDP Observation

Headless CDP attempted to open Multica at:

```text
http://localhost:3001/local-dev/agents
```

The browser was redirected to:

```text
http://localhost:3001/login
```

Fallback evidence:

- `multica-cdp-fallback.png`
- `multica-cdp-fallback.txt`

Because the browser session was not authenticated, Phase 3 used the Multica source anchor and the existing parity matrix as the authoritative behavior source.

### 2. Multica Source Read

Source files inspected for the task queue behavior:

- `/Users/martinlos/code/multica/server/internal/handler/task_lifecycle.go`
- `/Users/martinlos/code/multica/server/migrations/055_task_lease_and_retry.up.sql`
- `/Users/martinlos/code/multica/packages/views/agents/components/tabs/activity-tab.tsx`
- `/Users/martinlos/code/multica/packages/views/agents/components/tabs/task-failure.ts`
- `/Users/martinlos/code/multica/packages/views/issues/components/issue-detail.tsx`
- `/Users/martinlos/code/multica/packages/views/chat/components/task-status-pill.tsx`
- `/Users/martinlos/code/multica/packages/views/issues/components/terminate-task-confirm-dialog.tsx`

Relevant product semantics extracted:

- Agent tasks are task/run projections, not static profile data.
- Active tasks include queued/dispatched/running-style states.
- Terminal task rows retain status, failure reason, and recent work evidence.
- Retry/failure state is attached to task lifecycle data.

### 3. Ariadne Mapping

| Multica concept | Ariadne Phase 3 mapping |
| --- | --- |
| Agent | `AgentDefinition` persisted under `.ariadne/agents/{agent_id}.json` |
| Task | `TicketAssignment` projected as `AgentTaskItemDTO` |
| Task status | normalized from `AssignmentStatus` to queued / claimed / running / done / blocked / failed / cancelled |
| Attempt / retry | `TicketAssignment.attempt` and retry count projection |
| Blocker | `TicketAssignment.blocker` + `refresh_inbox()` assignment item |
| Agent Tasks tab | `GET /api/team/agents/{agent_id}/tasks` consumed by Team page detail tabs |

No separate Issue persistence was added.

## Browser Verification

Workbench URL:

```text
http://127.0.0.1:8766
```

Browser actions performed:

1. Opened `#team`.
2. Created a real AgentDefinition named `Phase 3 Codex 1782402810345`.
3. Opened `#issues/M0TR-001`.
4. Selected that agent in the Issue Detail assignment control.
5. Clicked `Assign`.
6. Opened the agent detail page.
7. Opened the `tasks` tab.
8. Verified `M0TR-001` appears as a task.

Screenshots:

- `issue-detail-assigned.png`
- `agent-tasks-tab.png`

API evidence:

- `issue-detail-api.json`
- `agent-tasks-api.json`
- `browser-verification.txt`

The observed task projection contains:

```text
task_id: assignment_12ecf14fc6cb
ticket_key: M0TR-001
agent_id: agent_4b050c358500
status: queued
attempt_number: 1
retry_count: 0
source: assignments
```

## Commands Run

```bash
python3.11 -m pytest tests/test_agent_definition_store.py -q
python3.11 -m pytest
ruff check .
cd frontend/ariadne-workbench && npm run build
python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8766
```

## Result

Phase 3 acceptance is satisfied for the non-running task queue surface:

- Issue Detail assigns to a real `AgentDefinition`.
- Agent Tasks tab reads real assignment projection.
- Task lifecycle fields are visible.
- Blocked assignment projection is covered by tests and links to Inbox when `refresh_inbox()` produces an item.

Runtime claim and activity streaming continue in Phase 4.
