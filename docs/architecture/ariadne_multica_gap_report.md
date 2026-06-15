# Ariadne / Multica Gap Report

This report compares Ariadne's local True MVP loop with the Multica
architecture inspected in `multica-ai/multica`.

## Implement Now

### AgentRun lifecycle state

Decision: implement.

Multica has explicit task lifecycle states. Ariadne already had `AgentRun`
status, but not a compatible lifecycle field. Ariadne now records
`lifecycle_state` as `created`, `running`, or `terminal` while keeping the
existing statuses for compatibility.

### Typed failure reasons

Decision: implement.

Multica's failure taxonomy prevents every failed task from collapsing into
free-form text. Ariadne now has a local `FailureReason` enum and persists it
on `AgentRun`, `ExecutionResult`, and `ReviewReport`.

### Runtime capability snapshots

Decision: implement.

Multica runtimes advertise CLI availability and execution capability. Ariadne
now writes `.ariadne/runtimes/capability_snapshot.json` from `backend doctor`
and from ticket runs.

### Project resources

Decision: implement.

Multica project resources are typed references. Ariadne now writes
`.ariadne/project/resources.json` with a local `ProjectResource` model for the
target repository.

### Local directory safety

Decision: implement.

Multica validates local-directory paths and serializes work per resolved path.
Ariadne now validates target repo paths and uses a local directory lock under
`.ariadne/locks/`.

### BuildSkill packs and handoff references

Decision: implement.

Ariadne now ships default `.skills/` packs and handoffs include a `## Skills`
section referencing them.

### Route decision artifact

Decision: implement.

Multica squads route through a leader. Ariadne's Build Lead now writes
`route_decision.json` before execution.

### Progress events

Decision: implement.

Ariadne now records progress events for route decision, execution, review,
memory, next tickets, and board export.

## Defer

### Full daemon queue

Decision: defer.

Ariadne is single-user and local. A durable queued/dispatched/claim protocol
would add operational weight before Ariadne needs multi-runtime scheduling.

### Heartbeat and offline recovery

Decision: defer.

The local MVP can surface runtime capability snapshots and blocked results
without a background daemon heartbeat loop.

### Provider-specific skill materialization

Decision: defer.

Ariadne references skills in handoffs. Copying skills into provider-specific
directories is useful later but not required for the current local loop.

### Session resumption

Decision: defer.

Multica stores `session_id` and `work_dir` for retry semantics. Ariadne has
compatible fields on `AgentRun`, but no automatic retry/resume behavior.

## Avoid

### Copying Multica server architecture

Decision: avoid.

PostgreSQL, WebSockets, cloud runtimes, auth, and workspace roles are outside
Ariadne's local-first MVP.

### Automatic commit or PR creation

Decision: avoid.

Both Multica local-directory docs and Ariadne safety rules keep agent edits
visible in the user's checkout without auto-commit, auto-push, or PR creation.

## Remaining Gaps

- No retrieval index over Ariadne memory.
- No queue with `queued -> dispatched -> running` granularity.
- No runtime heartbeat or automatic retry.
- No provider-specific skill injection.
- No UI beyond the static board.
