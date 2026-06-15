# Required Output — Ariadne Gap Report

Create:

```text
docs/architecture/ariadne_multica_gap_report.md
```

## Purpose

Compare Ariadne after PR #4 against Multica's architecture.

Use categories:

```text
A. Already good enough
B. Needs hardening now
C. Should be deferred
D. Should not copy
```

## Required evaluation areas

Evaluate:

```text
Build Ticket vs Multica Issue
Agent Run vs Multica Task
TicketRunOrchestrator vs Multica Task Lifecycle
Backend Doctor vs Runtime Dashboard / Runtime Registration
CodexBackend vs Daemon Runtime
Project Space vs Project Resources
Memory vs Skills
Next Tickets vs Autopilot / Follow-up Issue Generation
Board vs Multica Board
Reviewer vs Task Failure / Human Review
Build Lead vs Squad Leader
Execution Result vs TaskResult
Failure Reason vs taskfailure package
```

For each area:

```text
Current Ariadne behavior
Multica reference behavior
Gap
Risk if not fixed
Recommendation
Implement now / defer / avoid
```

## Required task extraction

At the end, produce a section:

```text
## Implementation Tasks From Gap Report
```

Each task must include:

```text
title
rationale
scope
acceptance criteria
affected modules
priority
```

The implementation tasks should map to the code changes you will make in this pass.
