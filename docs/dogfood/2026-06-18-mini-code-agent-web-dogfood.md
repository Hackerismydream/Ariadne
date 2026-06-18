# Mini Code Agent Web Dogfood Case

Date: 2026-06-18

Status: Proposed dogfood target

## One-Line Goal

Use Ariadne itself to help an AI Builder build a new local project called
`mini-code-agent`, from external knowledge input to issue generation to
Codex/Claude Code execution, entirely through the Ariadne Workbench web UI.

## Product Premise

Ariadne is not a code agent. Ariadne is a local Learning-to-Build workbench for
AI Builders.

The user brings:

- a project goal;
- a local project folder;
- external knowledge such as blogs, GitHub repositories, papers, notes, and
  codebase context.

Ariadne should:

1. ingest the external knowledge;
2. extract useful build decisions;
3. generate and update an issue set;
4. assign issues to Codex / Claude Code;
5. track runtime progress, blockers, review, memory, and next issues;
6. keep going until the project reaches a usable version.

The dogfood project is a test of that product loop.

## Dogfood Project

Target project folder:

```text
/Users/martinlos/code/ariadne-dogfood/mini-code-agent
```

Project name:

```text
mini-code-agent
```

Project goal:

```text
Build a Python mini code agent MVP for local AI Builders.

The tool should accept a coding task, call an LLM, run a small set of approved
local tools, iterate on observations, and produce a trace, diff, and test
result for the user to review.
```

The target project is separate from the Ariadne repository. Ariadne manages it;
Ariadne is not the target being built.

## External Knowledge Inputs

The first dogfood run should ingest these sources:

1. `https://minimal-agent.com/`
   - Use as the minimal agent-loop reference.
   - Relevant concepts: query model, parse action, execute action, observe,
     repeat, handle malformed output, handle execution exceptions.

2. `https://github.com/SWE-agent/mini-SWE-agent`
   - Use as the engineering reference.
   - Relevant concepts: small command-line agent, issue/task execution,
     shell-based interaction, simple trajectory, test result capture.

3. `https://github.com/LiuMengxuan04/MiniCode`
   - Use as the product/UX reference.
   - Relevant concepts: lightweight coding assistant, tool loop, terminal
     workflow, sessions, local skills, review-before-write behavior.

These sources are not implementation dependencies. Ariadne should extract
architecture and product lessons from them, not copy code.

## Web-Only Product Rule

This dogfood case must be implemented and accepted through the Ariadne
Workbench web UI.

The product path is:

```text
Workbench web UI
  -> create/register target project folder
  -> define project goal
  -> ingest external knowledge
  -> generate issue set
  -> assign issues to Codex / Claude Code
  -> daemon/runtime executes
  -> Workbench shows progress, blockers, review, memory, next issues, and version status
```

The following are not valid product acceptance paths:

```text
ari ingest ...
ari ticket run ...
ari demo full
python3.11 -m ariadne_ltb.cli ...
manual JSON edits under .ariadne/
static fixture/snapshot-only frontend data
```

CLI commands may still be used for automated tests, local debugging, and
fallback verification. They do not prove the dogfood product path is complete.

## Current Ariadne Problems This Dogfood Must Expose

The current Workbench has product gaps that this dogfood is intended to force
into the open:

| Area | Current behavior | Required dogfood behavior |
|---|---|---|
| Knowledge page | Buttons exist but do not perform real ingestion actions. | User can add URL / GitHub repo / local markdown knowledge from the web UI. |
| Goal page | Goal is display-only. | User can create/select a project goal and bind it to a target folder. |
| Issue page | Assign/run/watch partially works, but evidence panels are sparse. | Issues are generated from the dogfood knowledge and show real artifacts. |
| Agent page | Static agent table. | User can see which Codex/Claude-capable agents are assignable and why. |
| Runtime page | Route currently behaves incorrectly in browser testing. | Runtime status and daemon readiness are visible and accurate. |
| Skills page | Static skill list. | Handoffs show which build skills are referenced for the current issue. |
| Inbox page | Static inbox rows. | Blockers can be converted into repair issues or re-run decisions. |

## Required First Issue Set

When Ariadne processes the mini-code-agent goal and sources, it should create an
initial issue set similar to the following. The exact IDs can differ, but the
work must cover the same product surface.

```text
MCA-001 Bootstrap Python package and CLI
MCA-002 Add DeepSeek-backed LLM client configuration
MCA-003 Define tool protocol and model action schema
MCA-004 Implement shell command tool with allowlist
MCA-005 Implement file read and patch tools with review-before-write safety
MCA-006 Implement agent loop: prompt -> action -> observation -> repeat
MCA-007 Persist session trace and run summary
MCA-008 Capture git diff and test result
MCA-009 Add minimal reviewer checks for task completion
MCA-010 Write README quickstart and usage examples
```

These issues should be generated by Ariadne from the goal and sources, not
hand-entered as static frontend seed data.

## Dogfood MVP Acceptance

The dogfood is successful when a user can complete this flow from the web UI:

1. Open Ariadne Workbench.
2. Register target project:

   ```text
   /Users/martinlos/code/ariadne-dogfood/mini-code-agent
   ```

3. Create the project goal in the Workbench.
4. Add the three external knowledge sources.
5. Click a web action that generates the issue set.
6. Select `MCA-001`.
7. Assign it to Codex or Claude Code.
8. Start or confirm the local runtime path from the Workbench.
9. Watch the assignment progress in the Workbench.
10. See the produced artifacts in the Workbench:
    - build packet;
    - handoff;
    - execution result;
    - changed files;
    - test result;
    - review report;
    - memory entry;
    - next issue suggestions.
11. Repeat for enough issues that the target project has a runnable v0.1.

The target project v0.1 must support:

```bash
cd /Users/martinlos/code/ariadne-dogfood/mini-code-agent
python3.11 -m mini_code_agent --help
python3.11 -m mini_code_agent run "inspect this project and summarize next steps"
python3.11 -m pytest
```

Those commands are target-project verification commands. They are not the
Ariadne product path.

## Required Ariadne Product Changes

This dogfood requires Ariadne to add or complete these web-facing capabilities:

1. **Web project registration**
   - Register a local folder as a target project from the Workbench.
   - Show target path validity, git status, and test command configuration.

2. **Web goal creation**
   - Create/edit/select a project goal from the Workbench.
   - Bind the goal to a target project.

3. **Web knowledge ingestion**
   - Add URL, GitHub repository URL, local markdown, and local folder sources
     from the Workbench.
   - Store source records and show extraction status.

4. **Issue Factory**
   - Generate issue candidates from goal + sources + current project context.
   - Show proposed additions, updates, deferrals, and rejections.
   - Let the user apply the proposed issue delta from the Workbench.

5. **Web assignment and runtime control**
   - Assign an issue to Codex / Claude Code from the Workbench.
   - Show whether execution gates are ready.
   - Show daemon/runtime readiness.
   - Dispatch execution and stream assignment progress.

6. **Web evidence projection**
   - For each issue, show build packet, handoff, execution result, diff,
     tests, review, memory, and next issues.
   - Empty evidence panels must say whether evidence is missing, blocked,
     unconfigured, or not yet run.

7. **Web inbox recovery**
   - Convert blockers or review failures into repair issues.
   - Re-run or supersede issues from the Workbench.

## Non-Goals

Do not build these in the dogfood MVP:

- hosted auth;
- cloud workspace sync;
- full Multica clone;
- TUI for mini-code-agent;
- MCP marketplace;
- SWE-bench evaluation;
- automatic PR merge;
- automatic publish/release;
- copying MiniCode or mini-SWE-agent source code.

## Safety Boundaries

- Real Codex / Claude Code execution remains gated.
- Real external writes remain explicit and confirmed.
- Ariadne must not auto-commit, auto-push, auto-merge, or create PRs as part
  of the dogfood run.
- The Workbench may dispatch work, but the user must be able to inspect
  changed files and review results before landing anything.
- Secrets must not appear in Workbench projections, logs, artifacts, or docs.

## Implementation Sequence

Each phase must be independently mergeable and usable if the next phase never
lands.

### Phase 1: Remove Fake Product Surfaces From API Mode

Make API mode honest:

- Knowledge, goal, agent, runtime, skills, and inbox pages must not display
  static fixture data as if it were live product state.
- Disabled or unimplemented actions must say why.
- Fix the `#runtime` route behavior.

Acceptance:

- Opening the Workbench in API mode clearly distinguishes live data,
  unconfigured data, and offline fixture data.

### Phase 2: Web Project + Goal + Knowledge Input

Add web actions for:

- target project registration;
- project goal creation;
- external source ingestion.

Acceptance:

- The mini-code-agent target folder, goal, and three external sources can be
  created from the Workbench without Ariadne CLI commands.

### Phase 3: Web Issue Factory

Add web actions for:

- generating issue candidates from goal + sources;
- previewing issue deltas;
- applying issue deltas.

Acceptance:

- The MCA issue set is generated and appears on the issue board from the
  Workbench.

### Phase 4: Web Agent Execution Loop

Use existing CodexBackend / ClaudeCodeBackend orchestration through assignment
and daemon/runtime infrastructure.

Acceptance:

- `MCA-001` can be assigned and dispatched from the Workbench.
- The Workbench shows runtime claim, progress, blocker/success, and evidence.

### Phase 5: Version Completion Evidence

Show version-level progress for the target project.

Acceptance:

- Workbench can answer: what has been built, what passed, what failed, what is
  next, and whether mini-code-agent v0.1 is usable.

## Verification

Automated checks:

```bash
python3.11 -m pytest
ruff check .
cd frontend/ariadne-workbench && npm run build
```

Manual browser acceptance:

```text
Open Workbench
Register mini-code-agent target folder
Create goal
Add the three external sources
Generate and apply issue set
Assign and run MCA-001
Watch progress
Inspect evidence
Confirm target project CLI works
```

The manual acceptance must be done through the browser. CLI-only completion is
not accepted for this dogfood case.

