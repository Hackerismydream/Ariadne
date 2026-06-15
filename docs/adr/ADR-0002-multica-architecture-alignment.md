# ADR-0002: Multica Architecture Alignment

Status: Accepted

Date: 2026-06-15

## Context

Ariadne has a working True MVP loop and a safety-gated real CodexBackend smoke
path. The next risk is architecture drift: adding features as prompt-chain
helpers instead of strengthening the work-management kernel.

Multica's architecture was studied from `multica-ai/multica`, including its
agent/task/runtime/resource/skill documentation and server-side task lifecycle
queries.

## Decision

Ariadne will absorb selected Multica concepts as local Python primitives:

- `AgentRun.lifecycle_state`
- typed `FailureReason`
- `RuntimeCapability` snapshots
- `ProjectResource` snapshots
- target repo path validation
- local directory lock
- default BuildSkill packs
- handoff skill references
- `route_decision.json`
- ticket-run progress events
- board sections for the above

Ariadne will not copy Multica's server, queue, database, WebSocket daemon,
workspace permissions, cloud runtime, or UI architecture.

## Rationale

Ariadne's product shape is still local, deterministic, and ticket-driven. The
useful Multica lesson is not the infrastructure stack; it is the separation of
work carrier, run lifecycle, runtime capability, resource scope, progress, and
failure taxonomy.

This keeps Ariadne small while making future execution backends safer and more
inspectable.

## Consequences

Positive:

- Ticket runs now have explicit route and progress artifacts.
- Blocked execution has typed causes.
- Runtime and project context are persisted in local JSON.
- Board review can inspect capability/resource/skill context.
- Local target repos are protected by path validation and a directory lock.

Trade-offs:

- The lock is directory-level, not file-level.
- There is still no daemon heartbeat or retry queue.
- Skill references are visible in handoffs but not materialized into every
  provider's native skill directory.

## Security

External execution remains gated by `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1` and
`--confirm-execution`. Real Feishu writes remain gated by `FEISHU_ENABLE_WRITE=1`
and `--confirm-write`. Ariadne does not commit, push, merge, or create PRs
during backend execution.
