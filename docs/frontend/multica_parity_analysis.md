# Multica Parity Analysis for Ariadne Frontend

Date: 2026-06-17

## Scope

This analysis uses the local Multica deployment at `http://localhost:3001` as
the UI and interaction reference for a new Ariadne frontend. Ariadne should not
copy Multica's backend, auth, workspace hosting model, or full feature surface.
The frontend should adapt the issue-agent-runtime workbench pattern to
Ariadne's `/goal` product direction.

## Evidence Captured

Reference screenshots and API observations were captured locally under:

```text
.agent_context/multica_frontend_reference/
```

Captured pages:

- `issues.png`
- `project-detail.png`
- `agents.png`
- `runtimes.png`
- `skills.png`
- `inbox.png`
- `analysis.json`

These files are working evidence, not product assets.

## Multica Files Inspected

- `/Users/martinlos/code/multica/packages/ui/styles/tokens.css`
- `/Users/martinlos/code/multica/packages/ui/styles/base.css`
- `/Users/martinlos/code/multica/packages/views/layout/app-sidebar.tsx`
- `/Users/martinlos/code/multica/packages/views/issues/components/issues-page.tsx`
- `/Users/martinlos/code/multica/packages/views/issues/components/board-view.tsx`
- `/Users/martinlos/code/multica/packages/views/issues/components/board-column.tsx`
- `/Users/martinlos/code/multica/packages/views/issues/components/issue-detail.tsx`
- `/Users/martinlos/code/multica/packages/views/issues/components/execution-log-section.tsx`
- `/Users/martinlos/code/multica/packages/views/projects/components/project-detail.tsx`
- `/Users/martinlos/code/multica/packages/views/agents/components/agents-page.tsx`
- `/Users/martinlos/code/multica/packages/views/runtimes/components/runtimes-page.tsx`
- `/Users/martinlos/code/multica/packages/views/skills/components/skills-page.tsx`
- `/Users/martinlos/code/multica/packages/views/inbox/components/inbox-page.tsx`

## Product Surface to Rebuild for Ariadne

Required for Ariadne:

- App shell with sidebar and workspace navigation.
- `/goal` page for Ariadne's current goal, source knowledge, feedback, and
  state transitions.
- Issues kanban board grouped by ticket status.
- Issue detail inspector showing packet, assignment, runtime progress, review,
  memory, and next tickets.
- Agents page for Ariadne agent roles.
- Runtimes page for local daemon/backend capability.
- Skills page for BuildSkill packs.
- Inbox page for review, blocker, and feedback events.
- Floating agent chat dock as a read-only/product affordance for now.

Deferred or not required for Ariadne v1:

- Hosted auth.
- Multi-workspace membership management.
- Billing/usage.
- Full automation builder.
- Team/squad management beyond Ariadne agent roles.
- Real-time WebSocket collaboration.

## Visual System

The current Multica local UI is a quiet light workbench:

- Left sidebar, `240px` class width.
- White main workspace.
- Subtle gray surfaces, borders, and hover states.
- Compact typography, roughly 12px to 18px.
- Cards at about 8px to 10px radius.
- Kanban columns as muted vertical panels.
- Floating chat dock on the lower-right.

Tokens adapted from Multica:

```text
background: oklch(1 0 0)
foreground: oklch(0.141 0.005 285.823)
muted: oklch(0.967 0.001 286.375)
muted-foreground: oklch(0.552 0.016 285.938)
border: oklch(0.92 0.004 286.32)
brand: oklch(0.55 0.16 255)
sidebar: oklch(0.985 0 0)
sidebar-accent: oklch(0.95 0.002 286.375)
radius: 0.625rem
```

## API Shape Observed in Multica

Examples observed through browser network capture:

- `GET /api/workspaces`
- `GET /api/me`
- `GET /api/runtimes?workspace_id=...`
- `GET /api/agents?workspace_id=...&include_archived=true`
- `GET /api/agent-task-snapshot`
- `GET /api/issues?limit=50&status=backlog&sort=position`
- `GET /api/issues?limit=50&status=in_progress&sort=position`
- `GET /api/issues/child-progress`
- `GET /api/projects/:id`
- `GET /api/projects/:id/resources`
- `GET /api/inbox`
- `GET /api/chat/sessions?status=all`
- `GET /api/chat/pending-tasks`

Ariadne frontend should use its own adapter, not Multica APIs. The adapter
should expose local-first Ariadne data:

- goals
- tickets
- ticket detail
- agents
- runtimes
- skills
- inbox events
- progress timeline

## First Implementation Decision

Create an independent production frontend under:

```text
frontend/ariadne-workbench/
```

This is intentionally separate from `ariadne_ltb` core. It can later consume
Ariadne API or exported JSON data, but it starts with a typed local adapter and
seed data so the page system can be developed and screenshot-tested without
changing Ariadne's Python domain model.
