# Phase 8: Knowledge Orchestration Layer

Status: Active Phase 8 scope.

This document supersedes `2026-06-23-phase8-langgraph-handoff.md.superseded`.

## Scope

Phase 8 turns the source-to-issue path into a three-layer knowledge
orchestration system:

```text
Raw inputs: SourceDocument / AgentRun / ReviewReport / TicketComment
  -> ProjectKnowledge: ProjectPurpose, SourceInsight, SynthesisTheme,
     ContradictionRecord, BlockerLearning, OutcomesLog
  -> BuildTicket backlog preview
```

The product remains Ticket-centered. BuildTicket is still the work center and
there is no separate Issue persistence layer.

## Operations

- Ingest: LangGraph pipeline that analyzes changed sources and updates
  SourceInsight, SynthesisTheme, and ContradictionRecord files under
  `.ariadne/knowledge/<project_id>/`.
- Reflect: best-effort terminal AgentRun reflection into OutcomesLog and
  BlockerLearning.
- Compile: LangGraph pipeline that reads ProjectKnowledge and emits the same
  `CompiledIssueSpec` shape as the old deterministic compiler.
- Lint: deferred to Phase 9.

## Boundaries

- Do not add HTTP routes.
- Do not modify frontend code.
- Do not add independent Issue storage.
- Do not expose ProjectKnowledge over API in Phase 8.
- Keep `issue_compiler.py` as deterministic fallback.
- No DeepSeek key means the old compiler path must remain unchanged.

## Acceptance

```bash
python3.11 -m pytest
ruff check .
cd frontend/ariadne-workbench && npm run build
```

With `DEEPSEEK_API_KEY`, browser issue-delta generation should create
`.ariadne/knowledge/<project_id>/` and compile issues grounded in
ProjectKnowledge evidence. Without the key, existing deterministic tests must
continue to pass.

