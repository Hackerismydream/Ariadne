# Example Input - Multica Research Note

This is the seed input for the Ariadne MVP demo.

## Observation

Multica is a managed agents platform that turns coding agents into teammates.
The important idea is not just that there are many agents, but that agent
collaboration is organized around visible work objects such as issues, tasks,
assignments, comments, and runtime status.

## What Ariadne should learn

Ariadne should not copy Multica as a generic platform. Instead, it should absorb
the collaboration architecture and specialize it for Learning-to-Build.

The core mapping should be:

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

## Product decision

Ariadne 1.0 should not start by building a full web app or a full Multica clone.

It should start with a Python Mini-Multica-style Ticket Kernel:

- Build Ticket as visible work carrier;
- Build Packet as structured knowledge-to-build object;
- Agent Run as per-agent execution record;
- Artifact as reviewable output;
- deterministic local runtime;
- dry-run execution backend;
- conservative reviewer;
- Feishu write plan only;
- static board export.

## Why this matters

Without a Ticket-like carrier, a multi-agent system becomes hidden chat between
agents. It is difficult to visualize, debug, audit, review, or continue.

With Build Tickets, each iteration has:

- source;
- status;
- owner;
- evidence;
- plan;
- execution record;
- review result;
- memory write-back.

This is the foundation for a credible agent workbench.

## Suggested MVP Build Ticket

Title: Implement Ariadne MVP Ticket Kernel.

Decision: Build the local deterministic Python MVP with Build Ticket, Build
Packet, Agent Run, Artifact, dry-run execution, conservative review, Feishu
write plan, and static board export.
