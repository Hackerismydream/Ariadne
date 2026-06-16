# Ariadne v1.0 Multica Mapping

Status: Updated by
[`ADR-0004`](../adr/ADR-0004-ticket-centered-agent-workbench.md).

This document freezes Ariadne's relationship to Multica.

## Mapping Conclusion

```text
Multica = issue-centered agent work management
Ariadne = ticket-centered local agent workbench with knowledge/feedback backlog updates
```

Multica starts from existing issues:

```text
Issue
  -> Assign to Agent
  -> Agent executes
  -> Progress / blocker / result
```

Ariadne starts from sources, feedback, codebase context, memory, or an optional
goal, then updates tickets:

```text
Knowledge / Feedback / Codebase / Optional Goal
  -> Ticket Backlog Update
  -> Build Tickets
  -> Agent Assignment
  -> Daemon Worker
  -> Execution Agent
  -> Reviewer Agent
  -> Memory Agent
  -> Next Tickets / Board
  -> Ticket Backlog Update
```

## Concept Mapping

| Multica Concept | Ariadne Concept | Notes |
|---|---|---|
| Issue | BuildTicket | Work carrier and board unit |
| Task | AgentRun / TicketAssignment | One execution attempt or assignment |
| Agent | AgentProfile | Assignable teammate |
| Squad Leader | Build Lead Agent | Routing and assignment |
| Agent Comment | TicketComment | Agent progress, blocker, review |
| Daemon Runtime | LocalDaemonWorker | Local executor |
| Runtime Status | RuntimeCapability / WorkerHeartbeat | Backend availability and worker state |
| Skills | BuildSkill | Reusable work method |
| Project Resources | ProjectResource | Context boundary |
| Board | BuildBoard | Workbench presentation |
| Autopilot | Recurring ticket update | Future recurring work |
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

## Why Ariadne Is Not Just Multica Local

Multica is strongest when a user already has an issue and needs an agent
teammate to work it.

Ariadne is designed for AI builders whose project work changes as they read new
sources, run agents, review output, and inspect the codebase. Ariadne does not
replace the issue/ticket center with a global goal object. It keeps the ticket
as the work center and lets knowledge and feedback mutate the ticket backlog.

The difference is:

```text
Multica coordinates execution of known issues.
Ariadne updates the ticket set from knowledge and feedback, then coordinates execution.
```

## Why This Matters For v1.0

If Ariadne is described only as a CLI or fake-codex demo, it loses its product
shape. If Ariadne is described as BuildGoal-first, future agents will build the
wrong center of gravity. The frozen v1.0 interpretation is:

```text
Ticket-centered work management
  + knowledge / feedback / codebase driven backlog updates
  + Multica-style local agent runtime
  + safety-gated coding backends
  + review / memory / next-ticket loop
```
