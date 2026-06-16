# Ariadne v1.0 Multica Mapping

This document freezes Ariadne's relationship to Multica.

## Mapping Conclusion

```text
Multica = Issue-driven Agent Team
Ariadne = Goal-driven Agent Team
```

Multica starts from existing issues:

```text
Issue
  -> Assign to Agent
  -> Agent executes
  -> Progress / blocker / result
```

Ariadne starts from build goals and external knowledge:

```text
Build Goal
  -> Source / Knowledge / Repo Context
  -> Multi-Agent Planning
  -> Build Tickets
  -> Agent Assignment
  -> Daemon Worker
  -> Execution Agent
  -> Reviewer Agent
  -> Memory Agent
  -> Next Tickets / Board
```

## Concept Mapping

| Multica Concept | Ariadne Concept | Notes |
|---|---|---|
| Issue | BuildTicket | Work carrier |
| Task | AgentRun / TicketAssignment | One execution attempt or assignment |
| Agent | AgentProfile | Assignable teammate |
| Squad Leader | Build Lead Agent | Routing and assignment |
| Agent Comment | TicketComment | Agent progress, blocker, review |
| Daemon Runtime | LocalDaemonWorker | Local executor |
| Runtime Status | RuntimeCapability / WorkerHeartbeat | Backend availability and worker state |
| Skills | BuildSkill | Reusable work method |
| Project Resources | ProjectResource | Context boundary |
| Board | BuildBoard | Workbench presentation |
| Autopilot | Goal / Recurring Work | Future recurring work |
| Provider Matrix | Backend Capability Matrix | Codex / Claude / Shell capability differences |

## What Ariadne Adopts From Multica

Ariadne adopts the work-management lessons:

- agents should be visible teammates;
- work should have assignment and lifecycle state;
- runtime should be local and inspectable;
- progress, blockers, and reviews should be visible;
- provider capabilities should be explicit;
- resources and skills should be typed;
- board surfaces should explain what happened.

## What Ariadne Does Not Copy

Ariadne v1.0 does not copy:

- Go server;
- Postgres;
- multi-tenant workspace;
- complex permissions;
- WebSocket real-time collaboration;
- full daemon fleet;
- full frontend platform.

Ariadne v1.0 remains:

- Python;
- local-first;
- single-user;
- JSON / JSONL persistence;
- CLI plus static board or simple local serve;
- explicitly safety-gated.

## Why Ariadne Is Goal-Driven

Multica is strongest when a user already has an issue and needs an agent
teammate to work it.

Ariadne is designed for AI builders who are still deciding what should become
work. It uses build goals, source documents, project context, and memory to
produce tickets before coding agents execute.

The difference is:

```text
Multica coordinates execution of known issues.
Ariadne creates executable work from goals and knowledge, then coordinates execution.
```

## Why This Matters For v1.0

If Ariadne is described only as a CLI or fake-codex demo, it loses its product
shape. The frozen v1.0 interpretation is:

```text
Goal-driven upstream planning
  + Multica-style agent work management
  + safety-gated coding backends
  + review / memory / next-ticket loop
```
