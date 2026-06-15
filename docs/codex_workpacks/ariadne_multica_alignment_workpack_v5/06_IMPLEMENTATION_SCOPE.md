# Implementation Scope

Implement the highest-value architecture-hardening changes after writing the architecture digest, gap report, and ADR.

Do not implement everything Multica has.

## 1. Stronger Agent Run lifecycle

Ariadne Agent Run should model execution lifecycle more explicitly.

If changing enum values globally is safe, add states:

```text
created
queued
claimed
started
running
waiting_resource
succeeded
failed
blocked
cancelled
superseded
```

If broad enum changes are risky, keep existing status values and add a compatible lifecycle field:

```python
lifecycle_state: str
```

Required fields either directly on AgentRun or metadata:

```text
attempt
parent_run_id
superseded_by
failure_reason
started_at
ended_at
duration
backend_name
runtime_id optional
work_dir optional
session_id optional
```

Acceptance criteria:

```text
Every AgentRun has a terminal/non-terminal invariant.
Superseded runs are terminal.
Duration is computed or derivable.
Reviewer can reason about non-terminal runs.
Tests cover lifecycle transitions.
```

## 2. Typed failure reasons

Add failure reasons inspired by Multica.

Suggested enum:

```text
agent_error
runtime_offline
runtime_recovery
timeout
external_execution_blocked
command_unavailable
model_unsupported
test_failed
scope_violation
review_failed
user_cancelled
planner_failed
invalid_resource
resource_locked
unknown
```

Use these consistently in:

```text
ExecutionResult
ReviewReport
AgentRun
Next Tickets
Board
```

Acceptance criteria:

```text
Blocked external execution has external_execution_blocked.
Timeout has timeout.
Unavailable command has command_unavailable.
Target path validation failure has invalid_resource.
Directory lock failure has resource_locked.
```

## 3. Runtime capability model

Add:

```python
RuntimeCapability
```

Fields:

```text
id
provider
command
version
available
status
doctor_notes
checked_at
env_gates
```

`ari backend doctor` should persist a snapshot under:

```text
.ariadne/runtimes/
```

Board should display the latest runtime capability snapshot.

Acceptance criteria:

```text
Doctor still never prints secrets.
Runtime snapshot is persisted.
Board includes latest runtime snapshot.
Tests do not require Codex/Claude installed.
```

## 4. Project Space Resources

Add:

```python
ProjectResource
```

Fields:

```text
id
resource_type
resource_ref
label
created_at
```

Support at least:

```text
github_repo
local_directory
source_document
feishu_space
memory_dir
```

Write:

```text
.ariadne/project/resources.json
```

When a ticket runs, include scoped project resources in the handoff.

Acceptance criteria:

```text
Project resources serialize and load.
Handoff includes resources.
Demo target project is represented as local_directory resource.
Sources are represented as source_document resources.
```

## 5. Local directory safety

Before executing against a target repo, validate path.

Minimum rules:

```text
must be absolute or resolvable to absolute
must exist
must be directory
must be readable
must be writable
must not be /
must not be user's home directory
must not be /tmp, /var, /etc, /usr, /opt
must not resolve through symlink to a blocked path
```

If invalid:

```text
block execution before backend runs
failure_reason = invalid_resource
write artifact / event explaining why
```

Acceptance criteria:

```text
Invalid paths block execution.
Valid demo target path passes.
Tests cover blocked roots/home/temp/system paths where portable.
```

## 6. Directory lock

Add a simple local lock for target repo execution.

Suggested path:

```text
.ariadne/locks/<sha256-realpath>.lock
```

Default behavior:

```text
if locked, block with failure_reason=resource_locked
```

Do not implement long waiting by default.

Acceptance criteria:

```text
First lock acquisition succeeds.
Second acquisition blocks.
Lock is released after run.
Stale lock handling is documented.
```

## 7. Build Skills

Add minimal BuildSkill support.

Create default skill packs:

```text
.skills/codex-handoff/SKILL.md
.skills/review-diff/SKILL.md
.skills/feishu-write-plan/SKILL.md
```

Skill format:

```text
name
description
when_to_use
instructions
```

Planner/handoff should include skill references:

```text
## Skills
- codex-handoff
- review-diff
```

Acceptance criteria:

```text
Skills are discoverable.
Handoff references relevant skills.
Tests verify skill discovery and handoff inclusion.
```

## 8. Build Lead routing artifact

Implement minimal routing decision.

Create artifact:

```text
route_decision.json
```

Fields:

```text
ticket_id
ticket_key
selected_role
reason
not_selected_roles
confidence
created_at
```

This is Ariadne's minimal equivalent of squad leader evaluation.

Acceptance criteria:

```text
Every ticket run writes a route decision artifact.
Board shows route decision.
Tests verify artifact exists.
```

## 9. Progress events

Add events during ticket run:

```text
planned
handoff_written
execution_started
execution_finished
review_started
review_finished
memory_written
next_tickets_generated
board_exported
```

Acceptance criteria:

```text
Ticket event log includes these events in order.
Board shows progress events.
Tests verify event order for normal ticket run.
```

## 10. Smoke snapshot

Add:

```text
docs/smoke_test_results/ARI-004-real-codex-summary.md
```

Use scrubbed information only.

Include:

```text
commands attempted
failure modes encountered
final successful template
review verdict
changed files
lessons learned
```

Do not commit raw `.ariadne/` output.
