# Ariadne Capability Surface

This document freezes Ariadne's v1.x product capability surface.

Ariadne is a local-first, single-user, Python workbench for AI builders. Its
product form is:

```text
Goal-driven Multi-Agent Build Team
```

Learning-to-Build is the scenario. The product capability is the multi-agent
team that turns goals, sources, project context, and memory into executable
software iterations.

## Source Documents

This freeze integrates the capability-surface workpack under
`docs/capability_surface/`:

- `00_START_HERE.md`
- `01_PRODUCT_POSITIONING.md`
- `02_MULTICA_CAPABILITY_SURFACE.md`
- `03_ARIADNE_CAPABILITY_SURFACE.md`
- `04_CORE_OBJECT_MODEL.md`
- `05_PRIORITY_ROADMAP.md`
- `06_ACCEPTANCE_FRAMEWORK.md`
- `07_CODEX_MASTER_PROMPT.md`
- `aris/ARI-015-architecture-freeze.md` through
  `aris/ARI-025-workbench-board-productization.md`
- `templates/*.md`
- `ops/CODEX_IMPLEMENTATION_RULES.md`

## Target Users

Ariadne is for AI builders who already use coding agents and want a stronger
build loop around them:

- students or early-career engineers building agent and AI application projects;
- independent developers using Codex, Claude Code, Cursor, or similar tools;
- builders who read papers, blogs, and GitHub projects and want to convert
  learning into project iterations;
- developers who want coding agents to work from explicit context, acceptance
  criteria, project memory, and review feedback.

## Product Positioning

Ariadne answers the questions that become more important when writing code is
cheap:

```text
What should we build?
Why should we build it?
How does external knowledge relate to this repo?
How should the work be split for coding agents?
What context should Codex or Claude receive?
How do we review the result?
How do we remember the decision and create the next iteration?
```

The fixed product position is:

```text
Build Goal + External Knowledge + Project Context + Memory
  -> Multi-Agent Planning
  -> Build Tickets
  -> Agent Assignment
  -> Codex / Claude Execution
  -> Review
  -> Memory / Feishu Plan / Next Tickets
```

Ariadne remains local-first in v1.x:

- Python runtime;
- JSON / JSONL persistence;
- single-user local workbench;
- static board or simple local board server;
- dry-run Feishu by default;
- safety-gated external execution;
- no automatic commit, push, merge, or PR creation.

## Why Multica Is The Fixed Benchmark

Multica is the right architecture benchmark because it treats agents as
teammates in a work-management system, not as one-off prompt calls.

The important lesson is not only "upstream scheduling." Multica's capability
surface includes the operational layer that makes coding agents usable as a
team:

```text
Agent teammate
Task lifecycle
Daemon / runtime
Provider capability
Skills
Squads
Project resources
Comments
Board
Autopilot
```

Ariadne should not become a Multica clone. Ariadne should absorb the work
management capabilities while preserving its own upstream difference:

```text
Multica: existing issue -> assign agent -> task lifecycle -> result
Ariadne: build goal + knowledge + repo context -> tickets -> agent lifecycle -> result
```

## Multica Capability Surface

| Multica capability | Meaning | Ariadne interpretation |
|---|---|---|
| Agent teammate | Agents have identity, assignments, comments, blockers, and status | `AgentProfile`, `TicketAssignment`, `TicketComment`, board/journal surfaces |
| Task lifecycle | Work units can be queued, claimed, run, blocked, failed, retried, or cancelled | `TicketAssignment`, `AgentRun`, `FailureReason`, retry queue |
| Daemon / runtime | Local runtime claims work and executes local tools | `LocalDaemonWorker`, heartbeat, runtime journal, directory locks |
| Provider capability | Different coding providers have explicit capability differences | backend doctor, `RuntimeCapability`, future provider matrix |
| Skills | Reusable execution methods, not just docs | `.skills/`, `BuildSkill`, handoff references, future materialization |
| Squads | Leader routes work to team members | future `BuildTeam` and Build Lead routing |
| Project resources | Typed, scoped project context | `ProjectResource`, target repo validation, future richer resources |
| Comments | Conversation surface for progress and blockers | `TicketComment`, `ari ticket comments`, board comments |
| Board | Visible workbench for state and timeline | static board, `ari board serve` |
| Autopilot | Recurring or event-triggered work | future weekly review, source triage, memory summary, smoke checks |

## Ariadne Capabilities Already Covered

Current Ariadne already covers a useful local vertical slice:

| Capability | Current status |
|---|---|
| Source ingestion | Markdown source ingestion with source type inference and evidence snippets |
| Build Ticket | `BuildTicket` is the visible work carrier |
| Build Packet | structured source-to-build packet with evidence, tasks, acceptance criteria, risks, and quality metadata |
| Agent teammate | agent profiles, assignments, comments, runtime journal, board visibility |
| Ticket execution loop | planner, handoff, backend execution, tests, review, memory, Feishu dry-run, next tickets, board |
| FakeCodex backend | deterministic safe simulator for local demo |
| Real backend scaffolds | gated Codex and Claude Code adapters with command templates |
| Safety gate | external execution requires environment gate and explicit confirmation |
| Runtime | local daemon run-once/start, heartbeat, directory lock, recovery hints |
| Review and memory | conservative review, memory write-back, next ticket artifacts |
| Board | static markdown/html board and simple local serve |
| Multica alignment docs | architecture digest, gap report, ADR-0002 |

## Capabilities Still Needed

These gaps define the v1.x roadmap:

| Gap | Why it matters | Planned ARI |
|---|---|---|
| Build Goal | Ariadne must start from goals, not only sources or tickets | ARI-016 |
| Goal-to-ticket planning | Differentiates Ariadne from issue-driven systems | ARI-016 / ARI-017 |
| Build Team / Squad routing | Makes multi-agent positioning real | ARI-017 |
| Real Codex teammate as main demo | Proves Ariadne is not only fake-codex | ARI-018 |
| Provider capability matrix | Makes backend differences explicit and inspectable | ARI-019 |
| Skill materialization | Turns skills into execution method payloads | ARI-020 |
| Project resource boundaries | Gives agents scoped, typed context and safer execution | ARI-021 |
| Memory retrieval | Lets future planning use prior decisions and outcomes | ARI-022 |
| Review / eval agent | Improves quality judgment beyond simple rules | ARI-023 |
| Autopilot | Adds recurring review and source triage | ARI-024 |
| Workbench productization | Improves local visibility and demo quality | ARI-025 |

## ARI-015 To ARI-025 Priority

| Priority | ARI | Focus | Status |
|---|---|---|---|
| P0 | ARI-015 | Architecture freeze with Multica mapping | This document set |
| P0 | ARI-016 | Build Goal and goal-to-ticket planning | Next implementation candidate |
| P0 | ARI-017 | Build Team / squad routing | Next implementation candidate |
| P0 | ARI-018 | Real Codex teammate main demo | Next implementation candidate |
| P0 | ARI-019 | Provider capability matrix | Next implementation candidate |
| P1 | ARI-020 | Skill materialization | Planned |
| P1 | ARI-021 | Project resource boundaries | Planned |
| P1 | ARI-022 | Memory retrieval | Planned |
| P1 | ARI-023 | Review and evaluation agent | Planned |
| P2 | ARI-024 | Autopilot and recurring work | Planned |
| P2 | ARI-025 | Workbench board productization | Planned |

Implementation should proceed in small, reviewable slices. Each slice must keep
the existing true MVP path working:

```bash
ari ingest examples/sources/*.md
ari ticket list
ari ticket assign ARI-003 --to fake-codex
ari daemon run-once
ari export board
```

## Goal-Driven vs Issue-Driven

Multica is issue-driven:

```text
Issue -> Agent assignment -> Task execution -> Progress / review / result
```

This is strong once work already exists.

Ariadne is goal-driven:

```text
Build Goal
  -> Research / Knowledge / Project Context / Memory
  -> Build Tickets
  -> Agent assignment
  -> Codex / Claude execution
  -> Review / memory / next tickets
```

This is stronger for Learning-to-Build because the system helps decide what
should become work. The upstream goal-to-ticket transformation is Ariadne's
main product difference.

## Multi-Agent Is The Product, Learning-To-Build Is The Scenario

Learning-to-Build describes the user journey: learning from papers, blogs,
GitHub repos, project notes, and previous iterations, then turning that learning
into software.

The product mechanism is the multi-agent build team:

- Build Lead routes work.
- Research and Knowledge agents gather context.
- Project Context agent reads the current repo.
- Planner creates tickets and packets.
- Execution agent calls Codex, Claude, fake-codex, or another backend.
- Reviewer checks the result conservatively.
- Memory records the decision and generates next tickets.

This distinction matters for implementation. Ariadne should prioritize
capabilities that make agent teamwork explicit and inspectable, not only
capabilities that ingest more documents.

## Implementation Rules

Future ARI work must follow `ops/CODEX_IMPLEMENTATION_RULES.md`:

- do not rewrite Ariadne;
- do not fork Multica;
- do not introduce Go, Postgres, WebSockets, auth, or multi-tenancy for v1.x;
- do not break current CLI paths;
- do not require Codex, Claude, DeepSeek, Feishu, GitHub tokens, or network in
  tests;
- do not commit secrets;
- keep real external execution gated;
- each new capability needs CLI, model, persistence, tests, docs, safety gate,
  and failure path;
- each new capability must map to either Multica's capability surface or
  Ariadne's goal-driven difference.

## Acceptance Baseline

The capability freeze is docs-only. It should not change runtime behavior.

Required verification:

```bash
pytest
ruff check .
python3.11 -m ariadne_ltb.cli doctor v1
python3.11 -m ariadne_ltb.cli export board
```
