# CLI and Board UX

## Required CLI commands

```bash
ari ingest <paths...> [--planner deterministic|llm]
ari ticket list
ari ticket show <ticket_id_or_key>
ari ticket plan <ticket_id_or_key> --planner deterministic|llm
ari ticket run <ticket_id_or_key> --backend fake-codex
ari ticket run <ticket_id_or_key> --backend codex --confirm-execution
ari ticket run <ticket_id_or_key> --backend shell --command "..." --confirm-execution
ari export board
ari demo full
```

Fallback:

```bash
python -m ariadne_ltb.cli ...
```

## Main UX rule

The common path must be:

```bash
ari ingest examples/sources/*.md
ari ticket list
ari ticket run ARI-003 --backend fake-codex
ari export board
```

No extra manual execute/review/memory/export steps should be required.

## Board requirements

Board must show a top-level loop trace:

```text
Source -> Ticket -> Packet -> Handoff -> Backend -> Diff -> Tests -> Review -> Memory -> Feishu Plan -> Next Tickets
```

For each ticket, show:

- source type/title/path;
- ticket status;
- Build Packet decision;
- handoff artifact;
- backend;
- exit code;
- test exit code;
- changed files;
- diff artifact path;
- review verdict;
- memory path;
- Feishu plan path;
- next tickets path.

Markdown board is required.

HTML board can be simple, but should exist if already implemented.

## README

README must describe:

- what Ariadne is;
- how it differs from a demo harness;
- true MVP commands;
- safety model;
- optional real Codex / Claude / Feishu usage;
- no secrets committed;
- expected board/memory outputs.
