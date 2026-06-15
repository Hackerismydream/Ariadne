# ARI-005 — Multica Architecture Alignment

This workpack is for Codex.

Ariadne already has a usable local True MVP loop:

```text
ingest sources
  -> Build Tickets
  -> Build Packets
  -> ticket run
  -> backend execution
  -> review
  -> memory
  -> Feishu dry-run
  -> next tickets
  -> board
```

It also has a safety-gated real CodexBackend smoke-test path.

Now the goal is not to add another isolated feature. The goal is to prevent architecture drift by studying Multica deeply and aligning Ariadne with the parts of Multica that matter for agent work management.

## Mission

Study `https://github.com/multica-ai/multica` deeply, extract the architecture, compare it to Ariadne, and implement the highest-value Ariadne hardening changes.

This is not a request to copy Multica.

This is a request to absorb the architecture patterns:

```text
Issue-driven work
Task lifecycle
Agent as teammate
Runtime / daemon boundary
Project resources
Skills
Squad leader routing
Progress events
Failure recovery
Audit trail
```

## Expected end state

After this pass, Ariadne should still be a Pythonic, local-first, Learning-to-Build workbench. But it should have stronger architecture foundations:

```text
stronger AgentRun lifecycle
typed failure reasons
runtime capability snapshot
typed project resources
target repo path validation
local directory lock
BuildSkill support
route decision artifact
progress events
Multica architecture digest
Ariadne gap report
ADR-0002
```

## Non-goal

Do not turn Ariadne into Multica.

Do not build a server, web app, multi-workspace system, PostgreSQL backend, daemon fleet, or SaaS platform in this task.
