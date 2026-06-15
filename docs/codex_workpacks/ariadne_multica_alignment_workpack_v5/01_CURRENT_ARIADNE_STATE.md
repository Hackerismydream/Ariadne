# Current Ariadne State

Assume PR #4 has been merged or is the working base.

Current Ariadne capabilities:

```text
Build Ticket
Build Packet
Agent Run
Artifact
TicketRunOrchestrator
FakeCodexBackend
Safety-gated CodexBackend smoke test
Reviewer
Memory write-back
Feishu dry-run plan
Next Tickets
Board export
Backend doctor
```

Known strong points:

```text
ari ingest examples/sources/*.md
ari ticket list
ari ticket run ARI-003 --backend fake-codex
ari export board
ari backend doctor
ari backend smoke-test codex --confirm-execution
```

Known weaknesses:

```text
AgentRun lifecycle is still simpler than Multica's task lifecycle.
Failure reasons are not yet consistently typed across execution/review/orchestration.
Runtime capability is diagnostic output, not persisted architecture.
Project resources exist conceptually, but not as first-class typed resources.
Target repo safety is weaker than Multica's local_directory rules.
No directory lock / serialization around target repo execution.
BuildSkill exists conceptually but is not used like Multica skills.
Build Lead routing is not yet persisted as an explicit decision artifact.
Progress events are incomplete.
Multica influence exists, but is not yet formally captured after code-level review.
```

This task should close these gaps without expanding Ariadne into a large platform.
