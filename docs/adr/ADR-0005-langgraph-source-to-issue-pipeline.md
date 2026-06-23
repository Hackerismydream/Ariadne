# ADR-0005: ProjectKnowledge Source-to-Issue Pipeline

## Status

Accepted (revised)

## Context

Ariadne is a local-first, Ticket-centered Agent Workbench. BuildTicket remains
the work center. Goals are directional input, and `/api/issues` stays a
projection over BuildTicket.

The old source-to-issue compiler was deterministic and useful for offline
regression, but it did not create a compounding knowledge layer. It could not
incrementally absorb new sources, execution outcomes, review blockers, and
contradictions before generating the next BuildTicket backlog delta.

## Decision

Introduce a ProjectKnowledge layer between raw inputs and BuildTicket backlog:

```text
Layer 1 Raw Inputs
  SourceDocument / AgentRun.results / ReviewReport / TicketComment

Layer 2 ProjectKnowledge
  ProjectPurpose
  SourceInsight[]
  SynthesisTheme[]
  ContradictionRecord[]
  BlockerLearning[]
  OutcomesLog

Layer 3 BuildTicket Backlog
```

Layer 1 is immutable from the LLM's perspective. Layer 2 is the LLM-owned,
read-modify-write, persistent middle layer. Layer 3 stays the existing
BuildTicket backlog; no independent Issue persistence is introduced.

ProjectKnowledge is stored under:

```text
.ariadne/knowledge/<project_id>/
```

## Revision 2026-06-23

The original Phase 8 sketch proposed one LangGraph pipeline that directly
converted sources into issues. That design is superseded. It lacked persistent
intermediate knowledge, run feedback reflection, and ProjectPurpose grounding.

Phase 8 now uses two LangGraph pipelines plus one reflect function:

### Graph A: Ingest

```text
START
  -> prepare_changes
  -> analyze_source loop
  -> update_themes
  -> detect_contradictions
  -> END
```

The graph updates SourceInsight, SynthesisTheme, and ContradictionRecord.

### Graph B: Compile

```text
START
  -> load_knowledge
  -> plan_decomposition
  -> ground_evidence
  -> validate_dag
  -> quality_gate
  -> accept / retry <= 2 / fallback
```

The graph returns the same `CompiledIssueSpec` shape as the old compiler.

### Reflect

`reflect_on_run()` is not a graph. It is a best-effort terminal AgentRun hook
that appends OutcomesLog entries and updates BlockerLearning.

## Prompt Grounding

Every LLM node must put ProjectPurpose at the top of its prompt:

```text
You are working on project: ...
Why this project exists: ...
Target users: ...
Success signals to advance: ...
Out of scope (do NOT propose): ...
Engineering constraints: ...
```

If no explicit ProjectPurpose exists, Ariadne derives the minimal purpose from
the existing ProjectGoal title and north_star for backward compatibility.

## Dependencies

Add only:

```text
langgraph>=0.2
langchain-core>=0.3
```

Do not add `langchain-openai`, `langsmith`, or `langchain-community` for Phase
8. Ariadne wraps the existing DeepSeekClient instead.

## Fallback

No DeepSeek key, LLM failure, graph validation failure, or low-quality output
falls back to the existing deterministic `issue_compiler.py`.

This preserves CI and offline regression behavior.

## Non-Goals

- No HTTP routes for ProjectKnowledge in Phase 8.
- No frontend changes in Phase 8.
- No Query, Lint, or Memory layer in Phase 8.
- No vector database.
- No MemorySaver checkpoint. Layer 2 persistence is the checkpoint.
- No independent Issue model or storage.

## Consequences

Positive:

- Issue generation can compound over source, review, and run cycles.
- The intermediate knowledge is inspectable on disk.
- Existing BuildTicket-centered architecture is preserved.
- Tests can stay deterministic without external credentials.

Negative:

- The source-to-issue path now has more moving parts.
- Real quality depends on DeepSeek output and prompt quality.
- ProjectKnowledge needs a future Phase 9 UI/diagnostic surface, but must not be
  exposed as an API in Phase 8.

