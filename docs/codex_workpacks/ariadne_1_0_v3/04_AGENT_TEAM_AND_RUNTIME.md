# 04 — Agent Team and Runtime

## Runtime principle

The 1.0 runtime can still be mostly deterministic, but it must operate on real inputs and real target repo context.

If LLM API keys are available, implement optional LLM adapters. Tests must not depend on LLM APIs.

## Agent roles

### Build Lead Agent

Responsibilities:

- route source documents;
- choose source-specific specialist;
- prevent scope creep;
- select one buildable candidate for demo execution;
- enforce approval gates.

### Source Router Agent

Responsibilities:

- classify source type;
- normalize metadata;
- decide which specialist handles it.

### Research / Learning Agent

Handles paper/blog notes.

Outputs:

- insight summary;
- evidence snippets;
- project implications;
- candidate build decisions.

### GitHub / Repo Analysis Agent

Handles GitHub README/repo analysis notes.

Outputs:

- architecture patterns;
- APIs/CLI patterns worth borrowing;
- anti-patterns/out-of-scope items;
- candidate Build Packet.

### Knowledge Agent

Reads local historical memory:

- prior tickets;
- prior Build Packets;
- memory records;
- ADRs;
- docs.

Outputs:

- relevant prior decisions;
- possible conflicts;
- duplicate detection.

### Project Context Agent

Reads target repo and project space.

Outputs:

- file map;
- likely affected modules;
- test command;
- existing implementation summary;
- allowed scope recommendation.

### Planner Agent

Creates:

- Build Packet;
- Execution Plan;
- Coding Agent Handoff;
- acceptance criteria;
- allowed paths;
- test command.

### Execution Agent

Calls backend:

- dry-run;
- fake-codex;
- shell;
- optional codex;
- optional claude-code.

### Reviewer Agent

Inspects:

- packet quality;
- execution result;
- diff;
- tests;
- allowed scope;
- terminal run states;
- memory safety.

### Memory / Feishu Agent

Writes:

- local memory records;
- local decision logs;
- Feishu dry-run plans;
- optional confirmed Feishu API writes.

## Recommended pipeline for full demo

```text
Initialize Project Space
  -> Ingest 3 source documents
  -> Source Router for each source
  -> Specialist Agent for each source
  -> Knowledge Agent dedupe/conflict check
  -> Project Context Agent reads target repo
  -> Planner creates Build Packets
  -> Build Lead selects one code_task ticket
  -> Execution Agent executes against target repo
  -> Reviewer checks execution
  -> Memory Agent writes local memory + Feishu dry-run plan
  -> Board export
```

## LLM adapter interface

Implement a thin abstraction, but do not require keys:

```python
class LLMClient(Protocol):
    def complete_json(self, prompt: str, schema_name: str) -> dict: ...
```

Implement:

- RuleBasedLLM or DeterministicLLM for tests;
- optional OpenAIClient if `OPENAI_API_KEY` is set;
- optional AnthropicClient if `ANTHROPIC_API_KEY` is set.

If no keys are present, demo must still pass.
