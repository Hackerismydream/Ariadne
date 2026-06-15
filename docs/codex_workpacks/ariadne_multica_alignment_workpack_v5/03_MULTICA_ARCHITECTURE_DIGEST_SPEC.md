# Required Output — Multica Architecture Digest

Create:

```text
docs/architecture/multica_architecture_digest.md
```

This document is required.

## Required structure

### 1. Product thesis

Explain Multica as an architecture, not a marketing product.

Cover:

```text
agent as teammate
issue as work carrier
task as execution attempt
runtime as execution environment
daemon as local executor
skills as reusable capability packs
project resources as scoped context
squads as routing layer
autopilots as recurring task generation
```

### 2. Core domain object table

Create a table with columns:

```text
Multica object
Purpose
Important fields
Lifecycle
Ariadne equivalent
Implement now / defer / avoid
```

Include:

```text
Workspace
Project
ProjectResource
Issue
Agent
AgentTask / Task
Runtime
Daemon
Skill
Squad
Comment / Mention
Autopilot
TaskResult
TaskFailure
```

### 3. Task lifecycle

Document Multica task lifecycle in detail.

Include:

```text
queued
dispatched / claimed
started / running
waiting_local_directory
completed
failed
cancelled
retry / rerun
orphan recovery
runtime offline recovery
manual rerun
force fresh session
session pinning
```

Then compare to Ariadne.

### 4. Runtime / daemon model

Explain:

```text
daemon registration
runtime heartbeat
runtime liveness
CLI availability detection
task claim
task start
progress reporting
message reporting
task completion/failure
session_id and work_dir persistence
runtime recovery
```

### 5. Project resources

Explain:

```text
Project as resource container
resource_type discriminator
resource_ref typed JSON
github_repo
local_directory
per-daemon local_directory binding
local directory path validation
per-directory serialization
runtime artifacts outside user directory
```

Then propose Ariadne's Python version.

### 6. Skills

Explain:

```text
SKILL.md
supporting files
workspace skills
local skills
agent attachment
provider-specific injection path
safety of third-party skills
Skill vs MCP
```

Then propose Ariadne BuildSkill design.

### 7. Squads and leader routing

Explain:

```text
squad as first-class assignee
leader task
leader delegates by mention
leader records evaluation
leader stops after dispatch
anti-loop rules
dedup rules
```

Then propose Ariadne Build Lead / Router design.

### 8. Failure recovery

Document:

```text
orphaned task recovery
stale runtime detection
runtime heartbeat
task retry
manual rerun
force fresh session
session pinning
failure reasons
terminal state guarantees
```

Then propose Ariadne equivalents.

### 9. What Ariadne should not copy

Be explicit:

```text
no full web app clone
no Go/TS stack clone
no PostgreSQL requirement
no multi-workspace clone
no daemon fleet yet
no SaaS/server architecture in this task
no direct source copying
```

### 10. Citations / file references

For every major conclusion, reference the Multica files and symbols inspected.

Use a simple format:

```text
Source: server/internal/daemon/types.go — Task struct
Source: apps/docs/content/docs/project-resources.mdx — local_directory behavior
```
