# 05 — Inputs, Fixtures, and Demo Scenario

## Required source fixtures

Create:

```text
examples/sources/paper_agent_workflows.md
examples/sources/blog_multica_lessons.md
examples/sources/github_tiny_cli_readme.md
```

### paper_agent_workflows.md

Should look like a paper note about agent workflows, tool-use safety, evidence-backed actions, and evaluation.

It should imply a build action:

```text
Add Build Packet quality evaluation: evidence coverage, acceptance criteria quality, and scope risk score.
```

### blog_multica_lessons.md

Should summarize issue-driven agent collaboration and task lifecycle.

It should imply a build action:

```text
Improve Build Board and Agent Run timeline to show execution status and attempts.
```

### github_tiny_cli_readme.md

Should describe a small CLI project pattern.

It should imply a build action for the demo target repo:

```text
Add JSON export command to the target CLI project.
```

## Demo target project

Create target project:

```text
.ariadne/demo_target_project/
  pyproject.toml
  demo_todo/
    __init__.py
    cli.py
    store.py
  tests/
    test_cli.py
```

Initial feature:

- `demo-todo add "task"`
- `demo-todo list`

Buildable ticket should add:

- `demo-todo export-json`

Acceptance criteria:

- command exists;
- output is valid JSON list;
- tests pass;
- only target repo files are changed;
- Ariadne repo source files are not modified during execution demo.

## Why a separate target project matters

Ariadne must prove it can orchestrate development for another project, not just modify itself.

## Source ingestion behavior

`ari ingest examples/sources/*.md` should produce one ticket per source.

Each ticket should include:

- source type;
- title;
- summary;
- evidence snippets;
- candidate build decision;
- priority;
- links to source artifact.

## Candidate selection behavior

For `ari demo full`, Build Lead should select the GitHub README fixture ticket as the coding candidate because it maps cleanly to a small target-project feature.

The paper and blog tickets should still become Build Tickets/Build Packets and memory records, but may be categorized as experiment/doc_update/watchlist if not executed.
