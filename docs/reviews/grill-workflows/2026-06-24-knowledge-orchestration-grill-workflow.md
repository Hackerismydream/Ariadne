# Ariadne Grill Workflow B: Knowledge Orchestration Layer

## Purpose

Use this workflow in a new Codex or Claude thread to grill Ariadne's upper
knowledge-to-ticket layer.

This thread must answer one question:

```text
Why does Ariadne still fail to turn external knowledge and project goals into
real executable target-project work?
```

Scope is the upper layer only:

```text
Project purpose
External source ingestion
GitHub repo / code source understanding
Source artifacts
ProjectKnowledge
Issue Delta
Issue Factory
Handoff quality
Feedback -> next ticket mutation
Dogfood project closure
```

Do not review agent daemon internals here except where they expose missing
knowledge/handoff context.

## Required Skill And Subagent Rules

This workflow must use the `grill-me` skill:

```text
/Users/martinlos/.codex/skills/grill-me/SKILL.md
```

Use `grill-me` for its relentless `/grilling` standard: sharp questions,
branch-by-branch pressure, no vague praise, no shallow acceptance. Because this
workflow is intended for unattended review, do not pause after every question to
wait for the user. Convert the `grill-me` questioning style into the 5-round
candidate / reviewer / judge loop below.

Where this workflow requires independent reviewers, subagents are mandatory:

- If the environment provides a subagent or multi-agent tool, use it.
- If the environment cannot launch real subagents, simulate isolated subagents
  in separate markdown sections and clearly label them as `simulated subagent`.
- Do not collapse the four reviewer roles into one blended review.
- The Judge may merge only after all reviewer outputs exist.

## Required Reading

Read these Ariadne files first:

```text
/Users/martinlos/code/Ariadne/AGENTS.md
/Users/martinlos/code/Ariadne/README.md
/Users/martinlos/code/Ariadne/docs/adr/ADR-0004-ticket-centered-agent-workbench.md
/Users/martinlos/code/Ariadne/docs/adr/ADR-0005-langgraph-source-to-issue-pipeline.md
/Users/martinlos/code/Ariadne/docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md
/Users/martinlos/code/Ariadne/docs/superpowers/plans/2026-06-23-phase8-knowledge-orchestration-handoff.md
/Users/martinlos/code/Ariadne/docs/dogfood/2026-06-18-mini-code-agent-web-dogfood.md
```

Inspect these Ariadne implementation areas:

```text
/Users/martinlos/code/Ariadne/ariadne_ltb/knowledge
/Users/martinlos/code/Ariadne/ariadne_ltb/application/issue_factory.py
/Users/martinlos/code/Ariadne/ariadne_ltb/application/source_analysis.py
/Users/martinlos/code/Ariadne/ariadne_ltb/application/workbench_projection.py
/Users/martinlos/code/Ariadne/ariadne_ltb/application/current_version_scope.py
/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/sources
/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/plan-changes
/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/issues
```

Use Multica only as lower-layer reference. The core comparison here is not
"does Ariadne look like Multica"; it is:

```text
Ariadne should add a strong source / feedback / codebase -> ticket mutation
layer above Multica-style issue work.
```

## Hard Rules

- Do not implement fixes.
- Do not create new feature plans.
- Do not accept "it created some issues" as success.
- Do not accept fixed templates as knowledge reasoning.
- Do not count README-only GitHub scanning as repo understanding.
- Do not count CLI-only execution as browser dogfood closure.
- Every grill issue must cite concrete evidence: source artifact, knowledge
  file, issue delta, ticket body, handoff, browser behavior, API response, or
  target repo diff.

## Non-Negotiable Execution Requirement

You must execute exactly 5 rounds.

For every round, the working notes or final appendix must contain:

1. Candidate Generator: exactly 9 candidate grill questions.
2. Four independent reviewer subagent outputs.
3. Judge scoring and merge decision.
4. Round Ledger with keep / drop / merge / remaining gaps / next focus.

If the final output does not include evidence that all 5 rounds were executed,
the task is incomplete.

Do not compress the process into a single-pass review. Do not skip intermediate
ledgers. Do not produce the final list until Round 5 is complete.

Before writing the final file, self-check:

```text
Did I complete Round 1?
Did I complete Round 2?
Did I complete Round 3?
Did I complete Round 4?
Did I complete Round 5?
Does each round include 9 candidates, 4 reviewer outputs, and a Judge ledger?
```

If any answer is no, continue the workflow instead of finalizing.

## Browser And Artifact Checks

Start or use the running Workbench:

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8766
```

Use the browser to inspect:

```text
http://127.0.0.1:8766/#sources
http://127.0.0.1:8766/#plan-changes
http://127.0.0.1:8766/#issues
```

Inspect persisted state:

```bash
find /Users/martinlos/code/Ariadne/.ariadne -maxdepth 4 -type f | sort | sed -n '1,200p'
find /Users/martinlos/code/Ariadne/.ariadne/knowledge -maxdepth 5 -type f | sort 2>/dev/null
```

Inspect APIs:

```bash
curl -s http://127.0.0.1:8766/api/workbench
curl -s http://127.0.0.1:8766/api/sources
curl -s http://127.0.0.1:8766/api/issues
```

If a real dogfood run exists, inspect:

```text
.ariadne/dogfood/
.ariadne/artifacts/
target repo diff
target repo test output
review report
memory record
next issue artifact
```

## Five-Round Grill Loop

Run 5 rounds. Each round has 3 roles.

### Role 1: Candidate Generator

At the start of each round, generate exactly 9 candidate grill questions.

Each question must be:

- sharp;
- specific;
- falsifiable;
- non-duplicate;
- tied to the AI Builder product promise;
- tied to actual source-to-ticket evidence;
- answerable by code, browser, API, or artifact evidence.

Question format:

```markdown
### Candidate B<round>-<number>: <question>

- Product promise:
- Current observed behavior:
- Evidence to collect:
- Why this blocks dogfood closure:
```

### Role 2: Four Independent Reviewer Subagents

Launch four independent reviewer subagents. If true subagents are unavailable,
write four isolated `simulated subagent` markdown sections. They must not merge
their opinions before writing.

Reviewer 1: AI Builder User

- Focus: can a builder paste sources and understand how Ariadne turns them into
  work for the target project?
- Check: source input UX, lifecycle clarity, next action.

Reviewer 2: Knowledge Agent Engineer

- Focus: typed source artifacts, ProjectKnowledge, GitHub repo understanding,
  evidence grounding.
- Check: whether knowledge is genuinely extracted and persisted.

Reviewer 3: Issue Factory Reviewer

- Focus: issue delta quality and grounding.
- Check: whether tickets are derived from project purpose + sources + codebase
  state, not templates or Ariadne-self tasks.

Reviewer 4: Handoff And Dogfood Reviewer

- Focus: can generated tickets become good Codex / Claude handoffs and advance
  the target project?
- Check: allowed paths, tests, acceptance criteria, target repo evidence.

Each reviewer must output:

```markdown
## Reviewer <n> Round <round>

### Keep
- ...

### Drop
- ...

### Merge / Rewrite
- ...

### New Grill Questions
1. ...

### Evidence
- ...
```

### Role 3: Judge

Read all four reviewer outputs. Score every candidate using:

```text
importance: 0-5
verifiability: 0-5
deduplication: 0-5
dogfood impact: 0-5
risk exposure: 0-5
```

Then update a round ledger:

```markdown
## Round <round> Ledger

### Confirmed Grill Questions
- ...

### Eliminated Questions
- question:
  reason:

### Merged Questions
- from:
  into:
  reason:

### Remaining Gaps
- ...

### Next Round Focus
- ...
```

## Final Output

Write final output to:

```text
/Users/martinlos/code/Ariadne/docs/reviews/grill-workflows/results/YYYY-MM-DD-knowledge-orchestration-final-grill-list.md
```

The final file must contain exactly 20 to 25 high-quality grill issues for this
layer.

Each final issue must use this format:

```markdown
## KO-001: <question>

- Priority: P0 | P1 | P2
- Product promise:
- Ariadne evidence:
- Source / artifact evidence:
- Why this must be fixed:
- Verification method:
- Suggested owner area:
```

Also include:

```markdown
## Top 5 Structural Failures

## Where The Knowledge Layer Is Too Shallow

## Where The Product Still Feels Like Manual Notes

## Evidence Appendix
```

## Prompt To Paste Into New Thread

```text
You are reviewing Ariadne as the Knowledge Orchestration Grill thread.

You must use the grill-me skill:
/Users/martinlos/.codex/skills/grill-me/SKILL.md

Use grill-me's relentless /grilling standard, but do not pause for interactive
user answers. Convert that strict questioning style into the workflow below.

Where the workflow requires reviewer subagents, you must use real subagents if
the environment supports them. If real subagents are unavailable, simulate four
isolated reviewer subagents and label them as simulated subagents.

Read and follow:
/Users/martinlos/code/Ariadne/docs/reviews/grill-workflows/2026-06-24-knowledge-orchestration-grill-workflow.md

Your output must be the final markdown file requested by that workflow.
Do not implement fixes. Do not write a broad essay. Run the 5-round grill loop,
use browser/API/code/artifact evidence, and produce the final knowledge
orchestration grill list.

Non-negotiable execution requirement:

You must execute exactly 5 rounds.

For every round, your output or intermediate notes must contain:
1. Candidate Generator: exactly 9 candidate grill questions
2. Four independent reviewer subagent outputs
3. Judge scoring and merge decision
4. Round Ledger with keep/drop/merge/remaining gaps/next focus

If the final output does not include evidence that all 5 rounds were executed,
the task is incomplete.

Do not compress the process into a single-pass review.
Do not skip intermediate ledgers.
Do not produce the final list until Round 5 is complete.

Before writing the final file, self-check:
- Did I complete Round 1?
- Did I complete Round 2?
- Did I complete Round 3?
- Did I complete Round 4?
- Did I complete Round 5?
- Does each round include 9 candidates, 4 reviewer outputs, and a Judge ledger?

If any answer is no, continue the workflow instead of finalizing.
```
