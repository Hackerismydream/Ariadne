# Multica Agent Work Management Digest

Date: 2026-06-25

This digest summarizes the object boundaries, state model, and data flow extracted for the first Ariadne Multica Downstream Parity slice. It is intentionally scoped to Agents list, Create Agent, Agent Detail, Activity, Instructions, Skills, Environment, and Runtime Config.

## One Sentence

Multica treats an agent as a durable work-management actor with identity, runtime, instructions, skills, environment, task queue, activity, performance, and editable configuration; Ariadne currently treats agents mostly as default role/backend profiles plus assignment projections.

## Multica Object Boundary

### Agent

The Multica agent object is not a display row. It is a persisted actor.

Core fields observed from UI and handler/schema:

- Identity: `id`, `workspace_id`, `name`, `description`, `avatar_url`
- Ownership/access: `owner_id`, `visibility`, `archived_at`, `archived_by`
- Runtime: `runtime_id`, `runtime_mode`, `runtime_config`, `model`, `thinking_level`
- Behavior: `instructions`, `skills`, `custom_args`, `mcp_config`
- Secrets metadata: `has_custom_env`, `custom_env_key_count`
- Scheduling: `max_concurrent_tasks`
- Status/time: `status`, `created_at`, `updated_at`

Creation fields:

- `name`
- `description`
- `instructions`
- `avatar_url`
- `runtime_id`
- `runtime_config`
- `custom_env`
- `custom_args`
- `mcp_config`
- `visibility`
- `max_concurrent_tasks`
- `model`
- `thinking_level`
- `template`

Update fields:

- identity fields
- runtime fields
- instructions
- custom args
- MCP config
- visibility
- status
- concurrency
- model
- thinking level

Environment is deliberately excluded from normal update and normal response payloads. It uses a dedicated endpoint.

### Runtime

Runtime is both list metadata and execution capability. UI binds agents to runtimes and derives availability/presence from runtime health and task state.

Important Multica behavior:

- Agent row shows runtime name/health.
- Agent detail inspector lets the user change runtime.
- Runtime config tab is hidden unless the provider consumes it.
- Runtime-specific values are not normalized away; `thinking_level` remains runtime-native.

### Skills

Skills are agent-owned capabilities, not just global documentation.

Observed behavior:

- Create Agent can attach selected skills after creating the agent.
- Agent inspector shows skill chips.
- Skills tab adds/removes skills through `setAgentSkills`.
- Agent runtime payload carries skills to the daemon in `TaskAgentData`.

### Environment

Environment is agent-scoped and secret-safe.

Observed behavior:

- Normal agent payload exposes only `has_custom_env` and `custom_env_key_count`.
- Values are fetched only after the user clicks Reveal.
- Updates go through `updateAgentEnv`.
- Duplicate keys are blocked in the UI.
- Runtime config gateway tokens are masked and preserved with a sentinel.

### Task / Activity

Agent Activity is the default diagnostic surface.

Observed behavior:

- Now: active `queued`, `dispatched`, `running` workflow tasks.
- Last 30 days: total runs, success percentage, average duration, failed count, sparkline.
- Recent work: terminal `completed`, `failed`, `cancelled` tasks.
- Each task links to its issue and transcript.
- Active tasks can be cancelled.

Agent task data is not separate from issue/work state. The Activity tab joins:

- workspace task snapshot
- per-agent task list
- issue details
- task failure reason labels
- transcript access

## State Machine Signals

The first slice does not need to copy Multica's full task service, but Ariadne should preserve these state meanings:

```text
Agent Definition
  created -> active -> archived/restored

Agent Task
  queued -> dispatched/claimed -> running -> completed
                                      -> failed
                                      -> cancelled
                                      -> blocked

Agent Activity
  derived from tasks + runtime events + issue/run evidence
```

Multica's UI distinguishes "agent availability" from "last task status". Ariadne should do the same:

- Availability: can this agent/runtime accept work?
- Task state: what happened to assigned work?

## Data Flow

```text
Agent create/edit UI
        |
        v
Agent persisted object
        |
        +--> Agent list projection
        +--> Agent detail inspector
        +--> Instructions / Skills / Env / Runtime config tabs
        |
        v
Issue assigned to agent
        |
        v
Task / Assignment queue
        |
        v
Runtime claim and execution
        |
        v
Task events + run results + failure reasons
        |
        +--> Agent Activity
        +--> Agent Tasks
        +--> Issue Detail
        +--> Inbox / repair
```

## Ariadne Current State

Ariadne already has useful lower-level pieces:

- `AgentProfile` with `id`, `name`, `role`, `backend_name`, `planner_name`, `agent_runtime`, `backlog_planner_name`, `description`, `capabilities`, `default_confirm_execution`, `enabled`, `created_at`.
- `BuildTeam` with lead/implementer/reviewer/memory agent ids and `skill_refs`.
- `TicketAssignment` with `agent_id`, `agent_name`, `backend_name`, planner/runtime fields, lifecycle state, and blocker/failure metadata.
- `AgentRun`, `RuntimeEvent`, `ExecutionResult`, `ReviewReport`, and `InboxItem`.
- `/api/team/agents`, `/api/team/build-teams`, `/api/team/skills`.
- Workbench Team page that renders agents/build teams/skills.

But Ariadne's current agent layer is not Multica-grade:

- `ensure_default_agent_profiles()` auto-materializes default profiles, so the UI can show agent rows the user did not create.
- There is no browser create/edit/delete/archive flow for agents.
- There is no agent detail page.
- There is no per-agent activity/timeline projection.
- There is no per-agent task queue page.
- There are no per-agent instructions.
- There is no per-agent skill binding.
- There is no per-agent env metadata/reveal/update policy.
- There is no per-agent runtime config.
- Agent performance is not computed from run history.

## Ariadne Mapping

| Multica Concept | Ariadne Local-First Mapping |
| --- | --- |
| `Agent` | `AgentDefinition` persisted locally, replacing user-facing reliance on default `AgentProfile` rows |
| `AgentRuntime` | `RuntimeCapability` + per-agent `AgentRuntimeProfile` |
| `AgentTask` | `TicketAssignment` projection, joined with `BuildTicket`, `AgentRun`, and `RuntimeEvent` |
| `AgentActivity` | Derived event stream from assignments, runtime events, comments, artifacts, executions, reviews, inbox items |
| `Agent.skills` | `AgentDefinition.skill_ids` bound to discovered `BuildSkill` records |
| `Agent.instructions` | `AgentDefinition.instructions`, injected into route/handoff for assignments to that agent |
| `custom_env` | Secret-safe per-agent env metadata and local-only reveal/update path; default payload exposes key names/count/status only |
| `runtime_config` | Per-agent backend/runtime options such as Codex/Claude profile, model, reasoning, service tier, gateway/local mode where supported |

## First Implementation Spine

The next implementation should not start with UI imitation. It should build the smallest real downstream spine:

```text
AgentDefinition store
  -> Agents list from store
  -> Create Agent dialog writes store
  -> Agent Detail reads store
  -> Assign issue to agent_id
  -> Agent Activity/Tasks project TicketAssignment + RuntimeEvent + AgentRun
```

Only after that should Env and Runtime Config become editable. Otherwise Ariadne will repeat the previous failure: controls that look like Multica but are not backed by real product objects.

## Acceptance Rules For Phase 1-2

1. Browser-created agent persists across refresh.
2. Team page and Agent detail read the same persisted agent object.
3. Assigning an issue to the agent makes the assignment visible under that agent.
4. Running or blocking that assignment updates Agent Activity.
5. Instructions and skills are visible on the agent object and used by route/handoff evidence.
6. No mock/static/sample agent rows appear in product path.
7. Built-in/system agents, if retained, are explicitly labeled as system defaults and not presented as user-created teammates.

## Risks

- Adding a second issue/task store would violate Ariadne's ticket-centered rule. Agent Tasks must be a projection over `TicketAssignment`.
- Persisting env values incorrectly could leak secrets into Git. Env storage must be gitignored or reference external `.env` keys.
- Copying Multica's UI without state parity will increase demo feel. Every visible control must have a real API action or be absent.
- Default profile auto-materialization may keep producing misleading rows. Phase 1 must decide whether those defaults become system agents or move out of the user-facing list.
