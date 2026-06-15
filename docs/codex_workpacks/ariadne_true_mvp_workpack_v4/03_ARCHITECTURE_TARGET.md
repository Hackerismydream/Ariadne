# Architecture Target

## Main modules

The final implementation should have clear module boundaries.

Suggested modules:

```text
ariadne_ltb/orchestrator.py
ariadne_ltb/planner.py
ariadne_ltb/execution.py
ariadne_ltb/review.py
ariadne_ltb/memory.py
ariadne_ltb/next_tickets.py
ariadne_ltb/board.py
ariadne_ltb/cli.py
```

Existing modules may be reused. Do not rewrite working code unnecessarily.

## Core services

### TicketRunOrchestrator

Coordinates the complete product loop.

### PlannerBackend

Converts source/ticket/project context into BuildPacket and handoff.

Required implementations:

```text
DeterministicPlanner
LLMPlanner
```

### ExecutionBackend

Executes a coding task against a target project.

Required implementations:

```text
DryRunBackend
FakeCodexBackend
ShellBackend
CodexBackend
ClaudeCodeBackend
```

### Reviewer

Produces ReviewReport from BuildPacket + ExecutionResult + artifacts.

### MemoryWriter

Writes memory records, decision logs, weekly summaries, and Feishu dry-run plans.

### NextTicketGenerator

Turns review/memory output into next recommended Build Tickets.

### BoardExporter

Shows the full loop trace.

## Domain object expectations

The following concepts should be first-class and connected:

```text
SourceDocument
BuildTicket
BuildPacket
AgentRun
Artifact
ExecutionResult
ReviewReport
MemoryRecord
FeishuWritePlan
NextTicket
```

If `NextTicket` does not exist yet, either add it as a model or represent next tickets as a typed artifact with schema.

## Status expectations

Ticket statuses should make the workflow visible:

```text
inbox
planning
ready_for_execution
coding
reviewing
writing_memory
done
needs_fix
blocked
waiting_approval
```

## Artifact expectations

Artifacts should be stored under `.ariadne/artifacts/<ticket_id>/`.

The board should show relative paths when possible.

Required artifacts from a successful ticket run:

```text
build_packet.json
handoff.md
execution_log.json
git_diff.patch
changed_files.json
test_output.json
review_report.json
memory_record.json
feishu_write_plan.json
next_tickets.json or next_tickets.md
```
