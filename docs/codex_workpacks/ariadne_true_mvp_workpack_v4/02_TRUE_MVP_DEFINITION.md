# Ariadne True MVP Definition

## Product definition

Ariadne is a local Learning-to-Build Agent Team for AI builders.

It turns external knowledge into software iteration tasks and supervises coding backend execution.

## True MVP scope

Single user, single workspace, local-first, one active target repo at a time.

Required inputs:

- local Markdown sources;
- paper-like notes;
- blog-like notes;
- GitHub project / README-like notes;
- existing project memory under `.ariadne/memory/`.

Required outputs:

- Build Tickets;
- Build Packets;
- Codex / Claude handoff prompts;
- execution logs;
- git diff;
- changed files;
- test results;
- Review Reports;
- memory records;
- Feishu dry-run plans;
- next Build Tickets;
- Markdown and simple HTML board.

## Required core commands

```bash
ari ingest examples/sources/*.md
ari ticket list
ari ticket plan ARI-003 --planner deterministic
ari ticket run ARI-003 --backend fake-codex
ari export board
```

Fallback:

```bash
python -m ariadne_ltb.cli ingest examples/sources/*.md
python -m ariadne_ltb.cli ticket list
python -m ariadne_ltb.cli ticket plan ARI-003 --planner deterministic
python -m ariadne_ltb.cli ticket run ARI-003 --backend fake-codex
python -m ariadne_ltb.cli export board
```

## Required full loop

`ari ticket run <ticket>` must perform:

```text
load ticket
  -> load or create Build Packet
  -> create handoff artifact
  -> execute backend
  -> save execution artifacts
  -> review
  -> update ticket status
  -> write local memory
  -> generate Feishu dry-run plan
  -> generate next tickets artifact
  -> export board
```

## What is acceptable as local MVP

- Rule-based deterministic planner is acceptable as default.
- Optional LLM planner is required as a gated path, but tests must not require a key.
- FakeCodexBackend is acceptable as default demo executor, but it must be a validated simulator, not an unconditional patch script.
- Real Codex / Claude adapters may remain scaffolded, but they must be structurally useful and gated.

## What is not acceptable

- A demo-only implementation.
- A chain that only works through `ari demo full`.
- Requiring the user to manually call execute, review, memory, and board commands for the common path.
- CodexBackend that is just ShellBackend with a renamed class.
- LLM client file that is never used by planner/review paths.
- Next tickets only listed in a report by hand.
