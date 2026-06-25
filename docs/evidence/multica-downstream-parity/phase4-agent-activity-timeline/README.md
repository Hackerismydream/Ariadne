# Phase 4 Agent Activity Timeline Evidence

## Scope

Phase 4 makes Agent Activity a real event projection instead of a decorative tab.

Implemented behavior:

- Agent Activity reads assignment events through `RunEventService`.
- Issue Detail timeline reads the same assignment event resolver.
- Agent Activity renders Multica-style sections:
  - `Now`
  - `Last 30 days`
  - `Recent work`
  - `Activity stream`
- The same assignment event is visible in Agent Detail and Issue Detail.

## Three Anchors

### 1. CDP Observation

The Multica browser session for `http://localhost:3001/local-dev/agents/<agent-id>` was not authenticated in the headless browser and redirected to login. Phase 4 therefore used source-code observation plus the parity matrix as the behavior anchor.

Fallback browser evidence from Phase 3 remains applicable for this environment:

```text
docs/evidence/multica-downstream-parity/phase3-agent-task-queue/multica-cdp-fallback.png
docs/evidence/multica-downstream-parity/phase3-agent-task-queue/multica-cdp-fallback.txt
```

### 2. Multica Source Read

Source files inspected:

- `/Users/martinlos/code/multica/packages/views/agents/components/tabs/activity-tab.tsx`
- `/Users/martinlos/code/multica/packages/views/agents/components/agent-activity-hover-content.tsx`
- `/Users/martinlos/code/multica/packages/views/agents/components/agent-live-peek-card.tsx`
- `/Users/martinlos/code/multica/packages/views/agents/components/agent-presence-indicator.tsx`

Extracted semantics:

- Activity is the landing diagnostic surface for an agent.
- It groups current work, recent performance, and recent terminal work.
- Activity rows resolve to tasks/issues instead of being isolated log lines.
- Queued/running/failure states must come from runtime task data.

### 3. Ariadne Mapping

| Multica concept | Ariadne Phase 4 mapping |
| --- | --- |
| Agent task snapshot | `TicketAssignment` projected through `RunEventService` |
| Per-agent activity | `RunEventService.agent_assignment_events(agent_id)` |
| Issue timeline activity | `RunEventService.ticket_assignment_events(ticket_id)` |
| Now section | active or queued `AgentTaskItemDTO` records |
| Recent work | terminal `AgentTaskItemDTO` records |
| Last 30 days | `AgentRunItemDTO` terminal run projection |
| Event trace | shared assignment event id / ref id |

No new event store was added.

## Browser Verification

Workbench URL:

```text
http://127.0.0.1:8766
```

Browser actions performed:

1. Opened `#team/agents/agent_4b050c358500`.
2. Opened the `activity` tab.
3. Verified `Now`, `Last 30 days`, `Recent work`, and `Activity stream` are visible.
4. Verified `M0TR-001` appears in the agent activity surface.
5. Opened `#issues/M0TR-001`.
6. Verified Issue Detail timeline includes the same assignment event summary `assignment: queued`.

Screenshots:

- `agent-activity-timeline.png`
- `issue-detail-shared-timeline.png`

API evidence:

- `agent-activity-api.json`
- `issue-detail-api.json`
- `agent-activity-browser.txt`
- `issue-detail-browser.txt`

Shared event evidence:

```text
agent activity id: event_94e875323960
issue timeline id: assignment-event:event_94e875323960
summary: assignment: queued
ref_id: assignment_12ecf14fc6cb
```

## Commands Run

```bash
python3.11 -m pytest tests/test_agent_definition_store.py tests/test_assignment_timeline.py tests/test_multica_grade_workbench_api.py::test_issue_detail_timeline_and_comment_facade -q
ruff check .
cd frontend/ariadne-workbench && npm run build
python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8766
```

## Result

Phase 4 acceptance is satisfied for the local event projection:

- Agent Activity uses persisted assignment/runtime/comment events.
- Issue Detail timeline shares assignment events with Agent Activity.
- Browser evidence shows the Activity sections and shared issue timeline event.

Live WebSocket-style agent-wide push remains out of scope; Ariadne continues to use existing assignment event polling.
