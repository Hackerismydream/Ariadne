# 03 — Architecture and Domain Model

## Architecture layers

```text
CLI / Board
  -> Ticket Kernel
  -> Agent Runtime
  -> Source Ingestion
  -> Project Context
  -> Planning
  -> Execution Backends
  -> Reviewer
  -> Memory Write-back
```

## Domain model additions for 1.0

Keep existing models if present. Add or extend:

### SourceDocument

Represents an input source.

Fields:

- id
- source_type: paper | blog | github_repo | note | office_hour | review
- title
- path_or_url
- content_hash
- summary
- created_at
- metadata

### ProjectContext

Snapshot of current project/target repo.

Fields:

- id
- project_space_id
- target_repo_path
- top_level_files
- important_files
- README summary
- pyproject/package metadata
- test command
- existing tickets summary
- created_at

### ExecutionContext

Input to an execution backend.

Fields:

- ticket_id
- build_packet_id
- target_repo_path
- handoff_prompt
- backend_name
- allowed_paths
- command
- test_command
- confirm_execution
- timeout_seconds

### ExecutionResult

Output from backend.

Fields:

- id
- ticket_id
- backend_name
- dry_run
- command
- exit_code
- stdout
- stderr
- started_at
- ended_at
- git_head_before
- git_head_after
- git_status_before
- git_status_after
- changed_files
- diff_artifact_id
- execution_log_artifact_id
- test_command
- test_exit_code
- test_stdout
- test_stderr
- warnings

### MemoryRecord

Local project memory.

Fields:

- id
- ticket_id
- title
- decision_log_entry
- build_summary
- review_summary
- source_refs
- artifact_refs
- next_actions
- created_at

### Attempt / retry support

AgentRun should include:

- attempt: int
- parent_run_id: optional
- backend_name: optional
- terminal status required

Repeated runs should not silently overwrite prior attempts.

### Artifact path policy

Store relative paths for board portability:

```text
path = .ariadne/artifacts/<ticket_id>/<filename>
absolute_path = optional
```

## Status model

Ticket statuses:

```text
inbox
analyzing
planning
waiting_approval
ready_for_execution
coding
reviewing
needs_fix
writing_memory
done
blocked
failed
cancelled
```

Execution statuses:

```text
pending
running
succeeded
failed
blocked
skipped
cancelled
```

## Event sourcing minimum

Each ticket should be reconstructable from:

- ticket JSON;
- event log;
- run JSON;
- artifact index;
- artifact files.

No hidden state should be required.
