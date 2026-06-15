# Tests and Acceptance Criteria

## Required tests

Add or update tests for:

- `TicketRunOrchestrator` full loop;
- `demo full` uses the orchestrator;
- `ari ticket run ARI-003 --backend fake-codex` completes review + memory + board;
- FakeCodexBackend blocks when handoff/task does not mention `export-json`;
- FakeCodexBackend blocks when allowed paths do not include required files;
- CodexBackend disabled path returns blocked ExecutionResult;
- CodexBackend command-template rendering;
- ClaudeCodeBackend disabled path returns blocked ExecutionResult;
- deterministic planner creates valid BuildPacket from arbitrary markdown;
- LLM planner missing key fails gracefully;
- source ingestion extracts evidence snippets;
- next tickets artifact is generated after review;
- board includes Loop Trace;
- `.env` and `.ariadne/` are gitignored.

## Tests must not require

- network;
- Codex installed;
- Claude installed;
- DeepSeek key;
- Feishu credentials;
- GitHub token.

## Required commands

Run:

```bash
pytest
ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
```

If available:

```bash
uv run ari demo full
uv run ari export board
```

Manual flow to include in report:

```bash
uv run ari ingest examples/sources/*.md
uv run ari ticket list
uv run ari ticket run ARI-003 --backend fake-codex
uv run ari export board
```

## Definition of done

This pass is complete only if:

1. `ticket run` is the reusable full loop.
2. `demo full` calls the reusable full loop.
3. Running a ticket automatically writes review, memory, Feishu dry-run, next tickets, and board.
4. FakeCodexBackend is validated and can block unsafe/irrelevant tasks.
5. CodexBackend has proper command-template rendering and gating.
6. LLM planner is integrated as an optional path.
7. Tests pass without external credentials.
8. README and development report describe the true MVP.
