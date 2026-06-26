# Phase 6: Route Decision Uses Real Agents

Date: 2026-06-25

## Anchors

- Multica browser behavior: issue detail assigns work to a real agent identity, not a backend-only string. Ariadne browser verification used `http://127.0.0.1:8766/#issues/M0TR-004`.
- Multica source read:
  - `/Users/martinlos/code/multica/packages/views/issues/components/issue-detail.tsx`
  - `/Users/martinlos/code/multica/packages/views/agents/components/agent-row-actions.tsx`
  - `/Users/martinlos/code/multica/packages/views/agents/components/inspector/runtime-picker.tsx`
  - `/Users/martinlos/code/multica/server/internal/handler/task_lifecycle.go`
- Ariadne mapping: Multica issue assignment / agent picker maps to Ariadne `RouteDecision.agent_id`, `TicketAssignment.agent_id`, real `AgentDefinition.runtime_profile_id`, selected agent skills, and handoff packet evidence.

## Browser Verification

1. Opened `#issues/M0TR-004`.
2. Verified the agent selector showed the real persisted AgentDefinition `Phase 3 Codex 1782402810345 · codex · 1 skills`.
3. Clicked `Assign`.
4. Verified `M0TR-004` became assigned to `agent_4b050c358500`.
5. Verified the new assignment appears in the agent task projection.

## Evidence

- `issue-after-assign.png`
- `issue-detail-api.json`
- `route-decision.json`
- `handoff.md`
- `agent-tasks-api.json`
- `phase6-browser-verification.json`

## Result

`route-decision.json` records:

- `agent_id`: `agent_4b050c358500`
- `selected_agent_id`: `agent_4b050c358500`
- `runtime_profile_id`: `agent_4b050c358500:runtime`
- `selected_skills`: `skill_9179aec0c6a9`

The generated handoff includes the selected agent id, runtime profile, agent reason, selected skills, agent instructions, and environment key names.
