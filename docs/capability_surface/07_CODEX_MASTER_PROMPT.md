# Codex Master Prompt — Ariadne Capability Surface Freeze

Status: Superseded by
[`ADR-0004`](../adr/ADR-0004-ticket-centered-agent-workbench.md).

Do not implement the older BuildGoal-first / goal-first direction from this
file. It is preserved only as a historical record of the capability-surface
freeze that was later corrected.

The current product direction is:

```text
Ariadne = local-first Ticket-centered Agent Workbench
```

Current implementation guidance:

1. Keep Ariadne local-first, Python, single-user, JSON/JSONL-backed.
2. Keep Multica as the benchmark for issue/ticket work management.
3. Keep Ticket as the work center.
4. Let knowledge, feedback, review, memory, and codebase state update the
   ticket backlog.
5. Treat Goal as optional directional input, not as the root state machine.
6. Do not introduce Go, Postgres, WebSockets, auth, multi-tenancy, or a hosted
   frontend for v1.x.
7. Keep real Codex, Claude, and Feishu behavior safety-gated.

Current authoritative docs:

```text
docs/adr/ADR-0004-ticket-centered-agent-workbench.md
docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md
docs/capability_surface/ARIADNE_CAPABILITY_SURFACE.md
```
