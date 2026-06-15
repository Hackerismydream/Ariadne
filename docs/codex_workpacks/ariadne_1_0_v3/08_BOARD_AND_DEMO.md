# 08 — Board and Demo Requirements

## Static board required

Export:

```text
.ariadne/board/index.md
.ariadne/board/index.html
```

At least Markdown is required; HTML is strongly preferred if feasible.

Board must show:

- tickets grouped by status;
- source type;
- ticket title;
- priority;
- owner/latest agent;
- Build Packet decision;
- evidence count;
- execution backend;
- exit code;
- test exit code;
- changed files;
- diff artifact path;
- review verdict;
- memory write-back status;
- Feishu dry-run status;
- next action.

## Optional local read-only board server

If feasible, implement:

```bash
ari board serve --port 8765
```

Use FastAPI or stdlib HTTP server. No auth needed for local demo. Do not block 1.0 if this is too costly; static board must still exist.

## Full demo command

Required:

```bash
ari demo full
```

Fallback:

```bash
python -m ariadne_ltb.cli demo full
```

Expected output:

- created Project Space;
- created demo target repo;
- ingested 3 source fixtures;
- created 3 Build Tickets;
- selected one coding candidate;
- executed with FakeCodexBackend by default;
- captured target repo diff;
- ran target repo tests;
- generated review report;
- wrote local memory;
- generated Feishu dry-run plan;
- exported board.

## Optional real Codex demo

If `codex` is installed and authenticated:

```bash
ari demo full --backend codex --confirm-execution
```

If it is not available, Ariadne should clearly say so and suggest using `--backend fake-codex`.

## Demo success message

The final CLI output should include:

- number of sources ingested;
- number of tickets created;
- selected ticket key;
- backend used;
- changed files;
- tests passed/failed;
- reviewer verdict;
- board path;
- memory path;
- Feishu plan path;
- next recommended tickets.
