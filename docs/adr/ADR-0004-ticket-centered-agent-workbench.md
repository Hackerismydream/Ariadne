# ADR-0004: Ticket-Centered Agent Workbench

Status: Accepted

Date: 2026-06-16

## Context

Ariadne's earlier v1.0 docs described the product as a Goal-driven Multi-Agent
Build Team. That wording was useful while exploring the upstream planning
surface, but it now creates a harmful implementation bias: future agents may
try to build a BuildGoal-first planner instead of strengthening the working
ticket lifecycle.

The current product reality is already ticket-centered:

- sources are ingested into Build Tickets;
- tickets carry Build Packets, handoffs, assignments, runs, comments, artifacts,
  reviews, memory records, Feishu dry-run plans, and next-ticket suggestions;
- the local daemon claims assignments and runs tickets through local backends;
- the board shows the loop trace around ticket execution.

Multica remains the main architecture benchmark for agent work management. The
lesson Ariadne should keep is issue-centered agent work: assignable work,
agent teammates, task lifecycle, runtime/daemon state, comments, blockers,
reviews, skills, resources, and visible boards.

Ariadne's difference is upstream and feedback-driven ticket mutation:

```text
Multica lets agents work issues.
Ariadne lets knowledge and feedback update tickets, then lets agents work tickets.
```

## Decision

Ariadne v1.x is a local-first Ticket-centered Agent Workbench.

The center of the system is the Build Ticket, not a BuildGoal object.

Goals remain allowed as directional input, but they are not the root runtime
object, not the scheduler unit, and not the primary state machine.

The authoritative loop is:

```text
Knowledge / Feedback / Codebase
  -> update Ticket backlog
  -> Ticket management center
  -> assign to Agent
  -> local Daemon / Runtime
  -> Codex / Claude / fake-codex
  -> Review / Comments / Board / Memory
  -> update Ticket backlog again
```

## Consequences

Future implementation should prioritize:

- ticket lifecycle and assignment state;
- agent progress comments and blocker visibility;
- local daemon claim/recovery behavior;
- runtime capability and project resource boundaries;
- source, memory, review, and codebase feedback that creates, updates,
  prioritizes, downgrades, or closes tickets;
- board views that explain ticket state transitions.

Future implementation should not prioritize:

- a BuildGoal-first command surface as the next root workflow;
- a second state machine parallel to tickets and assignments;
- a Multica server clone with Postgres, multi-tenant auth, WebSockets, or a
  hosted frontend;
- automatic commit, push, merge, PR creation, or default external writes.

## Terminology

Use:

```text
Ticket-centered Agent Workbench
local-first Ticket-centered Agent Workbench
knowledge and feedback update the ticket backlog
Goal is directional input
Ticket is the work center
```

Avoid as current product positioning:

```text
Goal-driven Multi-Agent Build Team
BuildGoal-first flow
BuildGoal is the frozen v1.0 direction
Goal-to-Ticket is the next root workflow
```

These terms may still appear in historical or superseded documents if they are
explicitly marked as such.
