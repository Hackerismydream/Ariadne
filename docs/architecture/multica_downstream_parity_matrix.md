# Multica Downstream Parity Matrix

Date: 2026-06-25

This matrix is the Part A evidence pack for `docs/superpowers/plans/2026-06-25-multica-downstream-parity-phase-plan.md`.

It covers the first implementation slice for downstream parity: Agents list, Create Agent, Agent Detail, Activity, Instructions, Skills, Environment, and Runtime Config. The goal is not to clone Multica's Go/Postgres/auth stack. The goal is to reproduce the product semantics in Ariadne's local-first Python workbench.

## Source Files Inspected

Multica UI:

- `/Users/martinlos/code/multica/packages/views/agents/components/agents-page.tsx`
- `/Users/martinlos/code/multica/packages/views/agents/components/create-agent-dialog.tsx`
- `/Users/martinlos/code/multica/packages/views/agents/components/agent-detail-page.tsx`
- `/Users/martinlos/code/multica/packages/views/agents/components/agent-detail-inspector.tsx`
- `/Users/martinlos/code/multica/packages/views/agents/components/agent-profile-card.tsx`
- `/Users/martinlos/code/multica/packages/views/agents/components/avatar-picker.tsx`
- `/Users/martinlos/code/multica/packages/views/agents/components/agent-overview-pane.tsx`
- `/Users/martinlos/code/multica/packages/views/agents/components/tabs/activity-tab.tsx`
- `/Users/martinlos/code/multica/packages/views/agents/components/tabs/skills-tab.tsx`
- `/Users/martinlos/code/multica/packages/views/agents/components/tabs/env-tab.tsx`
- `/Users/martinlos/code/multica/packages/views/agents/components/tabs/instructions-tab.tsx`
- `/Users/martinlos/code/multica/packages/views/agents/components/tabs/runtime-config-tab.tsx`

Multica server/schema evidence:

- `/Users/martinlos/code/multica/server/internal/handler/agent.go`
- `/Users/martinlos/code/multica/server/internal/service/task.go`
- `/Users/martinlos/code/multica/server/pkg/db/queries/agent.sql`
- `/Users/martinlos/code/multica/server/migrations/001_init.up.sql`
- `/Users/martinlos/code/multica/server/migrations/095_agent_thinking_level.up.sql`

Ariadne current-state evidence:

- `/Users/martinlos/code/Ariadne/ariadne_ltb/models.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/storage.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/workbench_agents.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/dtos.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/mappers.py`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/team/TeamPage.tsx`

## Field And State Extraction

### Multica Agent Core Fields

Multica `AgentResponse` and DB schema expose an agent as a first-class work-management object:

- `id`
- `workspace_id`
- `runtime_id`
- `name`
- `description`
- `instructions`
- `avatar_url`
- `runtime_mode`
- `runtime_config`
- `custom_args`
- `mcp_config`
- `has_custom_env`
- `custom_env_key_count`
- `visibility`
- `status`
- `max_concurrent_tasks`
- `model`
- `thinking_level`
- `owner_id`
- `skills`
- `created_at`
- `updated_at`
- `archived_at`
- `archived_by`

Important safety behavior:

- Plaintext `custom_env` is not serialized on normal agent responses.
- Secret values require the audited `GET /api/agents/{id}/env` endpoint.
- Env writes use a dedicated endpoint instead of normal update.
- Runtime gateway tokens are masked in `runtime_config`.

### Multica Status And Enum Signals

- Agent visibility: `workspace`, `private`.
- Agent DB status: `idle`, `working`, `blocked`, `error`, `offline`.
- Activity task states rendered by Agent Activity: `queued`, `dispatched`, `running`, `completed`, `failed`, `cancelled`.
- Runtime config mode in OpenClaw UI: `local`, `gateway`.
- `thinking_level`: runtime-native string, nullable/empty means runtime default.

### Multica API Calls Observed In UI

- Agent list/detail:
  - `agentListOptions(wsId)`
  - `runtimeListOptions(wsId)`
  - `memberListOptions(wsId)`
  - `agentRunCounts30dOptions(wsId)`
  - `useWorkspacePresenceMap(wsId)`
  - `useWorkspaceActivityMap(wsId)`
  - fallback `api.getAgent(agentId)`
- Create/update:
  - `api.createAgent(data)`
  - `api.updateAgent(id, data)`
  - `api.archiveAgent(id)`
  - `api.restoreAgent(id)`
- Skills:
  - `skillListOptions(wsId)`
  - `api.setAgentSkills(agent.id, { skill_ids })`
- Env:
  - `api.getAgentEnv(agent.id)`
  - `api.updateAgentEnv(agent.id, { custom_env })`
- Activity/tasks:
  - `agentTaskSnapshotOptions(wsId)`
  - `agentTasksOptions(wsId, agent.id)`
  - `issueDetailOptions(wsId, issueId)`
  - `api.cancelTaskById(task.id)`

## Matrix

| Multica Surface | User Action | Visible Product Behavior | Underlying Objects | Multica Source Files | Ariadne Current State | Gap | Required Ariadne Object/API/UI | Browser Acceptance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Agents list | User opens Agents page, filters Mine/All/Archived, sorts by recent activity, clicks an agent row. | List displays real agents with name, description, visibility/private lock, owner, runtime, model, active/queued status, run count, last active, archived state, and row actions. The New Agent button opens a real create dialog. | `Agent`, `AgentRuntime`, `Member`, `AgentPresenceDetail`, `AgentActivity`, 30-day run counts. | `agents-page.tsx`; `agent-profile-card.tsx`; `agent.go`; `agent.sql`. | Ariadne has `AgentProfile` defaults in `models.py` and `storage.ensure_default_agent_profiles()`. `WorkbenchAgentsService.list_agents()` projects default profiles plus assignment counts. `TeamPage.tsx` renders a static table from `/api/team/agents`. | Agent rows are not user-created product objects. They lack owner, visibility, avatar, model, reasoning, runtime profile, env count, archived state, presence, and last-active/run metrics. Defaults are auto-materialized and can make the product appear to have agents the user never created. | Add local-first `AgentDefinition` persisted under `.ariadne/agents/*.json` or a compatible store family; add list/detail projections with owner=`local`, visibility, avatar, backend/runtime profile, model/reasoning, enabled/archived, active task counts, blocked counts, last run, and source=`agent_definition_store`. Team page must read only real persisted agents plus explicitly seeded built-ins marked as system agents. | In Ariadne browser, create two agents, refresh the page, filter/list them, and verify rows are backed by persisted local JSON. A fresh store with no user agents must not show fake user-created agents; built-ins must be labeled system/default if shown. |
| Create Agent | User clicks New Agent, fills avatar/name/description, visibility, runtime, model, instructions, skills, then creates. | Dialog validates name and runtime, supports avatar upload, workspace/private visibility, runtime picker, model dropdown, optional instructions, optional skills, duplicate mode, and post-create skill attach. Save creates an agent, invalidates list cache, closes dialog, and list updates. | `CreateAgentRequest`: `name`, `description`, `instructions`, `avatar_url`, `runtime_id`, `runtime_config`, `custom_env`, `custom_args`, `mcp_config`, `visibility`, `max_concurrent_tasks`, `model`, `thinking_level`, `template`; skill binding is a follow-up call. | `create-agent-dialog.tsx`; `avatar-picker.tsx`; `agent.go`; `agent.sql`. | Ariadne has no Workbench Create Agent action. `AgentProfile` can be saved as a list, but there is no browser CRUD endpoint and no UI dialog. | The selected Multica "New Agent" affordance has no Ariadne equivalent. Ariadne cannot create a named agent, choose backend/runtime, set instructions, or bind skills from the browser. | Add `POST /api/team/agents` with a strict local DTO: `name`, `description`, `backend_name`, `runtime_profile`, `model`, `reasoning_level`, `instructions`, `skill_ids`, `visibility`, `max_concurrent_assignments`, `enabled`. Add a Workbench dialog. Runtime choices must be derived from `RuntimeCapability`, not hardcoded. | In browser: click New Agent, create "Mini Code Implementer" with Codex backend and one skill, refresh, verify it persists and appears in the list and detail page. Invalid missing name/backend must show a recoverable validation error. |
| Agent Detail / Activity | User opens an agent, lands on Activity tab, checks what it is doing now, recent performance, and recent work. User can cancel active task and open issue/transcript. | Activity is the diagnostic landing tab. It shows Now, Last 30 days, Recent work, success percentage, average duration, failed count, sparkline, active tasks, terminal tasks, issue links, transcript buttons, failure reason labels, and cancel action for active tasks. | `Agent`, `AgentTask`, `Issue`, `AgentActivity`, workspace task snapshot, per-agent task list, issue detail cache, task failure reason. | `agent-detail-page.tsx`; `agent-overview-pane.tsx`; `activity-tab.tsx`; `task.go`. | Ariadne has `TicketAssignment`, `AgentRun`, `RuntimeEvent`, `ExecutionResult`, `ReviewReport`, `InboxItem`, and `/api/assignments/{id}/events`. It does not have an Agent Detail page. Team page only shows active/blocked counts. | There is no per-agent fact center. Activity exists as assignment events but is attached to issue/run surfaces, not to agent identity. No 30-day per-agent summary, no current/recent tasks grouped under an agent, no cancel/repair affordance at agent level. | Add `GET /api/team/agents/{agent_id}` and `GET /api/team/agents/{agent_id}/activity` as projections from `AgentDefinition`, `TicketAssignment`, `AgentRun`, `RuntimeEvent`, `ExecutionResult`, and `ReviewReport`. Add Activity tab with Now/Recent/Performance sections. Do not invent events; empty states must say no persisted activity. | Assign a real issue to an agent. Activity shows queued. Run daemon or produce a blocked execution. Activity updates to running or blocked using the same assignment/run evidence shown in Issue Detail. |
| Agent Detail / Instructions | User opens Instructions tab, edits the agent prompt/instructions, sees dirty state, saves, and tab switch is guarded when unsaved changes exist. | Rich editor loads `agent.instructions`, tracks dirty local draft, saves via agent update, and prevents silent loss on tab switch. | `Agent.instructions`; `UpdateAgentRequest.instructions`; dirty state owned by `AgentOverviewPane`. | `agent-overview-pane.tsx`; `instructions-tab.tsx`; `agent-detail-page.tsx`; `agent.go`; `agent.sql`. | Ariadne `AgentProfile` has only `description` and capabilities; no `instructions` field. Handoff generation uses route/planner content and BuildSkill material, not per-agent persistent instructions. | Agent identity cannot carry durable instructions. There is no browser UI to edit agent behavior, and no path to include per-agent instructions in handoff/runtime execution. | Extend `AgentDefinition` with `instructions`; expose PATCH endpoint; show Instructions tab; include instructions in route/handoff packet generation for assignments to that agent. | Create an agent, add instructions in browser, assign an issue to it, and verify the generated handoff/evidence references the agent instructions or records that none were configured. |
| Agent Detail / Skills | User opens Skills tab, sees attached skills, adds a workspace skill, removes a skill. | Skills tab lists attached skills with name/description, disables Add when workspace has zero skills, uses `SkillAddDialog`, and writes the full skill id set with `api.setAgentSkills`. Inspector also shows compact skill chips. | `Agent.skills`, workspace `Skill`, `AgentSkillSummary`, agent-to-skill binding. | `skills-tab.tsx`; `agent-detail-inspector.tsx`; `create-agent-dialog.tsx`; `agent-profile-card.tsx`. | Ariadne has `BuildSkill` discovery from `.skills/` / `.ariadne` and `BuildTeam.skill_refs`. Team page lists skills globally. There is no `AgentProfile.skill_ids` or per-agent binding. | Skills exist as global material or build-team refs, not as agent-owned capabilities. Route Decision and handoff cannot prove "this agent used these skills". | Add `skill_ids` to `AgentDefinition`; add `GET/PATCH /api/team/agents/{agent_id}/skills`; Agent detail Skills tab; route decision should select `agent_id` and `selected_skill_ids`; handoff should render those skills; run evidence should record `used_skills`. | In browser: attach a skill to an agent, refresh detail, verify chip remains. Assign issue to agent; route/handoff/evidence must show the selected skill id. Removing the skill must prevent future route decisions from selecting it for that agent. |
| Agent Detail / Environment | User opens Environment tab. Before reveal, only key count is shown. User intentionally reveals env values, edits keys/values, saves, and duplicate keys are blocked. | Secrets are not present in normal agent payload. Pre-reveal state shows only configured-key count and a reveal action. Reveal fetches dedicated env endpoint. Save writes dedicated env endpoint. Values can be hidden/shown locally. Duplicate keys are rejected. | `Agent.has_custom_env`, `Agent.custom_env_key_count`, dedicated env endpoint, audited secret read/write, `custom_env` map. | `env-tab.tsx`; `agent.go`; `agent.sql`. | Ariadne stores runtime capabilities and environment gates globally (`ARIADNE_ENABLE_EXTERNAL_EXECUTION`, backend command availability, DeepSeek/Feishu/GitHub gates). No per-agent env key metadata or audited reveal/edit endpoint exists. | Agent-specific env is absent. Workbench cannot show whether an agent has configured credentials/options without exposing secrets. No safe per-agent env editing model exists. | Add `AgentEnvironmentProfile` with key metadata and secret-safe storage policy. For v1 local single-user, allow storing values only in `.env` references or an `.ariadne/agents/<id>.env.json` file that is gitignored; product API must expose `key_count` and key names/status by default, never values. Add explicit reveal/update endpoint gated by local-only UI. | Browser shows "0 variables configured" for new agent. Add `DEEPSEEK_API_KEY` or `ANTHROPIC_API_KEY` as configured key, refresh, key count remains. API list/detail must not include secret values. |
| Agent Detail / Runtime Config | User opens Routing/Runtime Config tab when the selected runtime supports it, chooses local/gateway routing, fills gateway host/port/token/TLS, and saves. Unsaved changes are tracked. | Runtime Config tab is provider-gated. OpenClaw shows local/gateway mode. Token is masked/preserved. Save patches `runtime_config`. Unsupported runtimes hide the tab to avoid footguns. | `Agent.runtime_config`, runtime provider, `OpenclawRuntimeConfig`, gateway token mask, `UpdateAgentRequest.runtime_config`. | `agent-overview-pane.tsx`; `runtime-config-tab.tsx`; `agent-detail-inspector.tsx`; `agent.go`; `095_agent_thinking_level.up.sql`. | Ariadne has backend names (`codex`, `claude-code`, etc.) and `RuntimeCapability`, but no per-agent runtime_config object. External execution gates are global/env based. | Runtime behavior cannot be configured per agent. Users cannot choose local vs gateway or agent-specific backend options from the Workbench. | Add `AgentRuntimeProfile` inside `AgentDefinition`: `backend_name`, `runtime_mode`, `model`, `reasoning_level`, `service_tier`, `max_concurrent_assignments`, `runtime_config`, `external_execution_policy`. Hide config sections when backend does not support them. Validate Codex service tier against known allowed values (`fast` or `flex`) when applicable. | Browser can edit a Codex agent to `service_tier=flex` and reasoning level. Runtime capability shows whether Codex/Claude is available. Assignment to that agent uses its runtime profile and records it in evidence. |

## Required Phase 1-2 Cut

The minimum independently mergeable cut should implement only the rows needed to remove fake agent surfaces:

1. `Agents list`
2. `Create Agent`
3. `Agent Detail / Activity` skeleton backed by real assignment/run events
4. `Agent Detail / Instructions`
5. `Agent Detail / Skills`

`Environment` and `Runtime Config` can be scoped to read-only or metadata-only in the first merge if secret handling would otherwise expand the slice too far. They still need matrix rows now so the model does not paint itself into a corner.

## Non-Parity Boundaries

Ariadne must not copy these Multica implementation details:

- Workspace auth and member permissions.
- Go handler and Postgres schema.
- Cloud runtime registry.
- Hosted file upload/CDN avatar storage.
- Multica issue persistence model.

Ariadne should copy these product semantics:

- Agent as first-class object.
- Agent-owned instructions, skills, runtime profile, and env metadata.
- Activity as the default diagnostic tab.
- Agent tasks and activity derived from the same task/run state as issue detail.
- Secret values absent from default agent payloads.
- Runtime config hidden unless the backend consumes it.
