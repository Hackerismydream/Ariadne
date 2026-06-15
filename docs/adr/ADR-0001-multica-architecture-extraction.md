# ADR-0001 - Extracting Multica's Collaboration Architecture for Ariadne

## Status

Accepted for v0.1 MVP.

## Context

Ariadne is a Learning-to-Build Agent Team. It needs a visible, assignable,
auditable collaboration model for multiple agents that turns source knowledge
into coding-agent context and reviewable artifacts.

Multica is a useful reference because it organizes coding agents around issues,
tasks/runs, agents, squads, project resources, skills, local runtimes, and board
visibility. Ariadne uses that lesson without copying Multica as a full managed
agents platform.

## Decision

Ariadne will borrow the collaboration architecture and specialize it for
Learning-to-Build:

```text
Multica Issue             -> Ariadne Build Ticket
Multica Task / Run        -> Ariadne Agent Run
Multica Agent             -> Ariadne Agent Role
Multica Squad Leader      -> Ariadne Build Lead Agent
Multica Project Resources -> Ariadne Project Space
Multica Skills            -> Ariadne Build Skills
Multica Local Daemon      -> Ariadne Local Runner
Multica Board             -> Ariadne Build Board
```

The MVP keeps these objects separate:

- Build Ticket: visible work carrier, status, owner, timeline, and board card.
- Build Packet: structured knowledge-to-build object inside the ticket.
- Agent Run: one execution by one role against one ticket.
- Artifact: durable plan, packet, handoff, dry-run result, review, write plan,
  or board export.

## What Ariadne does not borrow

Ariadne v0.1 does not borrow Multica's full web application, daemon fleet,
cloud runtime, external provider execution, workspace administration, or
autonomous issue execution. Those are out of scope until the ticket kernel,
handoff quality, dry-run safety, and review loop are proven locally.

## Runtime and safety

The MVP uses a deterministic local runtime and JSON persistence. Deterministic
agent nodes prove the lifecycle without requiring an LLM API, Codex, Claude
Code, Feishu, a crawler, a vector database, or network access.

Execution is dry-run only. The backend writes a planned execution artifact and
test plan; it never commits, pushes, merges, opens PRs, calls external APIs, or
edits external systems.

Feishu is treated as memory/write-back, not the primary execution engine. The
MVP generates a Feishu write plan with `dry_run=true`; it performs no API calls.

## Consequences

Benefits:

- small and reviewable MVP;
- visible ticket lifecycle;
- terminal Agent Run states;
- inspectable artifacts under `.ariadne/`;
- conservative review before memory write-back;
- clear path to future Codex and Feishu adapters.

Tradeoffs:

- no real web UI in v0.1;
- no real runtime daemon in v0.1;
- no real Codex execution in v0.1;
- no real Feishu API write in v0.1;
- no multi-workspace or auth features.

## Risks

Agent collaboration systems commonly fail through stale runtime state, hidden
running state, duplicate tasks, unclear ownership, invisible failures, and
external side effects that are not represented in the work record.

Ariadne v0.1 mitigates those risks by requiring:

- terminal status for every Agent Run;
- visible event timeline on every Build Ticket;
- artifacts linked to tickets and runs;
- deterministic persistence;
- dry-run external execution;
- conservative reviewer output;
- inspectable static board export.
