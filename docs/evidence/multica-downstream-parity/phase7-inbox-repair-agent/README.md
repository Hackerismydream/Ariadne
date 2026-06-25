# Phase 7: Inbox / Repair Integrated With Agent

Date: 2026-06-25

## Anchors

- Multica browser behavior: blocked task produces an inbox item; repair creates follow-up work that remains tied to the responsible agent.
- Multica source read:
  - `/Users/martinlos/code/multica/server/internal/handler/task_lifecycle.go`
  - `/Users/martinlos/code/multica/packages/views/inbox/components/inbox-page.tsx`
  - `/Users/martinlos/code/multica/packages/views/inbox/components/inbox-list-item.tsx`
  - `/Users/martinlos/code/multica/packages/views/agents/components/tabs/task-failure.ts`
- Ariadne mapping: `InboxItem.agent_id` + `RepairAction` + repair assignment against the same `AgentDefinition`.

## Verification

Input blocker:

- Issue: `M0TR-004`
- Source assignment: `assignment_55fdcd30a8f4`
- Agent: `agent_4b050c358500`
- Failure reason: `agent_error`

Workbench API action:

```text
POST /api/inbox/inbox_60aa9b4e6dc8/repair
```

Result:

- Repair ticket: `ARI-077`
- Repair assignment: `assignment_e8cc969fc650`
- Repair assignment agent: `agent_4b050c358500`
- Agent Tasks projection contains the repair assignment.
- `.ariadne/inbox/repair_actions.json` records the repair action.

Computer Use could not attach to the Chrome window during this phase (`cgWindowNotFound`), so the browser interaction evidence is represented by Workbench HTTP API responses and system screenshots.

## Evidence

- `inbox-before-repair.png`
- `inbox-after-repair.png`
- `inbox-before-repair-api.json`
- `repair-response.json`
- `inbox-after-repair-api.json`
- `agent-tasks-after-repair-api.json`
- `repair-actions.json`
- `phase7-browser-api-verification.json`
