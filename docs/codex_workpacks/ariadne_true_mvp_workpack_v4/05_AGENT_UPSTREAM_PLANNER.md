# Agent Upstream and Planner Specification

## Goal

Implement the missing "upstream Agent" layer.

Ariadne must not only execute fixed demo tasks. It must convert source content into Build Packets and handoff prompts.

## Planner interface

Create a planner abstraction.

Suggested file:

```text
ariadne_ltb/planner.py
```

Suggested API:

```python
class PlannerBackend(Protocol):
    name: str
    def plan_ticket(self, store: AriadneStore, ticket: BuildTicket) -> PlannerResult: ...
```

Required planners:

```text
DeterministicPlanner
LLMPlanner
```

## DeterministicPlanner

Default planner. Must be stable and testable.

It should:

- read the ticket source;
- extract title;
- extract 2-5 evidence snippets;
- infer source type;
- infer build decision;
- infer tasks;
- infer acceptance criteria;
- infer affected modules;
- write a Build Packet;
- write a handoff artifact.

For the demo GitHub README fixture, it may choose the target task:

```text
Add demo-todo export-json support.
```

For arbitrary markdown, it should not always force the same demo task. It should create archive/watchlist/doc/experiment/code decisions based on content.

## LLMPlanner

Optional, gated.

Use the existing `default_llm()` / DeepSeek client if available.

CLI:

```bash
ari ticket plan ARI-003 --planner llm
```

Behavior:

- if `DEEPSEEK_API_KEY` is missing, fail gracefully and save a blocked planner artifact;
- if LLM returns invalid JSON, save error artifact and leave existing Build Packet unchanged;
- never require LLM for tests;
- validate output against BuildPacket schema.

## LLM prompt output schema

The LLM planner should ask for JSON with:

```json
{
  "source_summary": "",
  "insight": "",
  "evidence": [
    {
      "quote_or_summary": "",
      "location": "",
      "confidence": 0.0
    }
  ],
  "project_relevance": "",
  "build_decision": "archive|watchlist|doc_update|experiment|code_task|architecture_change|reject_for_now",
  "tasks": [],
  "acceptance_criteria": [],
  "affected_modules": [],
  "risks": [],
  "assumptions": []
}
```

## Required planner commands

```bash
ari ticket plan <ticket_id_or_key> --planner deterministic
ari ticket plan <ticket_id_or_key> --planner llm
```

`ticket run` should call the planner automatically when necessary.
