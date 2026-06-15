# 01 — Review of v2 Workpack and New 1.0 Target

## Why the previous v2 workpack was insufficient for 1.0

The previous startup pack intentionally targeted a local deterministic Ticket Kernel. It was useful for bootstrapping the domain model, persistence, pipeline, artifacts, and board. However, it was too conservative for the user's actual loop goal.

It explicitly avoided:

- real Codex/Claude execution;
- real or optional Feishu integration;
- retrieval over external inputs;
- generic ticket creation from multiple source types;
- project-aware source-to-build reasoning;
- coding backend execution against another target project;
- full Learning-to-Build demo.

That means it produced a kernel, not a product.

## Ariadne 1.0 target

Ariadne 1.0 should be the smallest complete product demo:

```text
External knowledge -> Build Ticket -> Build Packet -> Plan -> Execute -> Review -> Memory -> Board
```

It must support at least these demo inputs:

1. a paper-like markdown note;
2. a blog/architecture note;
3. a GitHub README/repo analysis note.

It must execute against a separate demo target repo/project. The execution backend can be safe shell or fake-codex by default, with optional real Codex CLI support when installed.

## Non-negotiable 1.0 demo outcome

A user should be able to run one command from a clean repo:

```bash
ari demo full
```

Fallback:

```bash
python -m ariadne_ltb.cli demo full
```

That command should:

1. create or reset a demo workspace;
2. create a separate target project under `.ariadne/demo_target_project/`;
3. ingest three external source fixtures;
4. generate three Build Tickets and Build Packets;
5. select one buildable ticket as the implementation candidate;
6. generate a coding-agent handoff;
7. execute safely against the target project;
8. capture logs and git diff;
9. run tests;
10. review the result;
11. write local memory artifacts;
12. generate Feishu dry-run write plan;
13. export or serve a board showing the complete trace.

If `codex` is installed and the user passes `--backend codex --confirm-execution`, Ariadne may call Codex CLI. Otherwise the default demo must still work without external services.
