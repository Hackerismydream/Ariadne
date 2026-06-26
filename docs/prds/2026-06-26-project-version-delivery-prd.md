# Ariadne Project Version Delivery PRD

Created: 2026-06-26

## Problem Statement

AI builders already use Codex, Claude Code, review agents, planning agents, and
external reference material while building software. The current workflow has
too much manual switching: the user reads a repo or blog, asks one agent to make
a plan, moves context to another agent, asks a coding agent to implement, then
manually reviews diffs, failures, and follow-up work.

Ariadne is meant to remove that coordination burden. The product should let an
AI builder choose a target project version, add external knowledge, confirm the
generated issue delta, assign work to a local agent team, run real Codex or
Claude Code against the target project, and inspect execution evidence in the
browser.

The current Ariadne implementation has many useful components, but they are not
locked into one browser-driven product loop. Sources, issue generation, agents,
runtime, inbox, evidence, and memory exist as pieces. The user still cannot
reliably complete the full path from external knowledge to a target project
version being advanced by a real coding agent.

## Solution

Build the Ariadne v1 Project Version Delivery flow.

The primary user experience is a browser Workbench centered on the current
Project Version. The user creates or selects a target project, sets the target
version goal, adds a GitHub repository and a blog or Markdown source, reviews an
LLM-generated Issue Delta, applies selected issues into the Current Version
Issue Set, assigns a current issue to a real Codex or Claude Code agent, starts
or connects the local daemon, and watches the assignment progress through real
backend execution.

The successful dogfood scenario is a new `mini-code-agent` project advanced to
v0.1. The target project must implement a minimal coding loop: accept a local
repo and task, run a safe provider or coding step, write trajectory/log output,
capture a diff, run a test command, and expose reviewable evidence.

Ariadne must not use `fake-codex`, `demo full`, static fixtures, CLI-only
success, or mini-code-agent hardcoded templates as product acceptance. The
implementation path can use deterministic tests and offline fixtures for
engineering safety, but the product acceptance path must use the browser
Workbench and a real Codex or Claude Code execution attempt.

## User Stories

1. As an AI builder, I want to create or select a target project folder in the browser, so that Ariadne knows which project I am trying to advance.
2. As an AI builder, I want to set a target version such as v0.1, so that all sources, issues, assignments, and evidence are scoped to one deliverable.
3. As an AI builder, I want to describe the goal for the target version, so that Ariadne can judge which external knowledge matters.
4. As an AI builder, I want to add a GitHub repository as an external source, so that Ariadne can learn from existing open-source implementations.
5. As an AI builder, I want to add a blog or Markdown source, so that Ariadne can learn design principles and product constraints.
6. As an AI builder, I want Ariadne to analyze a GitHub repository beyond the README, so that issues are grounded in architecture, entrypoints, tests, and reusable patterns.
7. As an AI builder, I want Ariadne to analyze a blog source into claims and evidence, so that generated issues cite product or design rationale.
8. As an AI builder, I want each source to show analysis status, artifacts, and evidence, so that I know whether it is ready to influence planning.
9. As an AI builder, I want Ariadne to generate an Issue Delta from the target version, sources, and target codebase, so that I do not manually translate knowledge into work.
10. As an AI builder, I want each proposed issue to show evidence, reason, affected module, and acceptance criteria, so that I can trust or reject the proposal.
11. As an AI builder, I want to confirm the Issue Delta before it changes the Current Version Issue Set, so that Ariadne does not mutate my project plan without review.
12. As an AI builder, I want applied issues to be clearly scoped to the current project version, so that historical or unrelated tickets do not pollute the board.
13. As an AI builder, I want generated issues to target the mini-code-agent project rather than Ariadne itself, so that dogfood proves target project delivery.
14. As an AI builder, I want generated issues to come from a general source-to-issue compiler, so that the flow is not secretly hardcoded for mini-code-agent.
15. As an AI builder, I want to select one current issue and assign it to a real agent, so that I control exactly what runs next.
16. As an AI builder, I want to see which agent owns an issue, so that the work-management layer feels like an agent team rather than a background script.
17. As an AI builder, I want Agent Detail to show current tasks, recent activity, skills, instructions, and environment, so that I understand what the agent can do.
18. As an AI builder, I want the daemon to claim the selected assignment rather than an old queued assignment, so that the Workbench remains predictable.
19. As an AI builder, I want runtime capability to show Codex and Claude Code availability, so that I know whether a real backend can run.
20. As an AI builder, I want Ariadne to write a real handoff packet for the coding agent, so that Codex or Claude Code receives target repo, evidence, constraints, and acceptance criteria.
21. As an AI builder, I want Codex or Claude Code to actually run against the target project, so that Ariadne proves it can orchestrate real coding agents.
22. As an AI builder, I want blocked execution to show exact evidence and repair steps, so that a failure is actionable instead of hidden.
23. As an AI builder, I want blocked execution to be a diagnostic state rather than a success state, so that the product does not claim closure without real execution.
24. As an AI builder, I want stdout, stderr, exit code, changed files, diff, and test result captured, so that I can audit what the coding agent did.
25. As an AI builder, I want review results to appear beside the issue and run evidence, so that I can judge whether the implementation met acceptance criteria.
26. As an AI builder, I want Inbox items for blockers and repair actions, so that failures have a visible recovery path.
27. As an AI builder, I want memory and next-issue suggestions after a run, so that execution feedback changes future planning.
28. As an AI builder, I want Current Version progress to update after runs, so that I can see whether v0.1 is getting closer.
29. As an AI builder, I want closure evidence to be generated automatically, so that the result can be reviewed without reconstructing the run manually.
30. As an AI builder, I want closure evidence to include browser path, assignment, backend, handoff, diff, tests, review, inbox, memory, and next issues, so that success or failure is objective.
31. As an AI builder, I want the dogfood acceptance to require a real Codex or Claude Code run, so that Ariadne does not regress into fake or dry-run demos.
32. As an AI builder, I want deterministic tests to remain available, so that engineering safety does not require external credentials.
33. As an Ariadne maintainer, I want product acceptance separated from offline regression, so that contributors do not confuse fixture success with product success.
34. As an Ariadne maintainer, I want all issues and assignments to remain BuildTicket-centered, so that the system stays aligned with the existing architecture.
35. As an Ariadne maintainer, I want no separate Issue persistence layer, so that Workbench issues remain product projections of BuildTickets.
36. As an Ariadne maintainer, I want Multica behavior alignment without copying its hosted stack, so that Ariadne remains local-first Python.
37. As an Ariadne maintainer, I want each implementation slice to reduce browser delivery friction, so that work does not drift into isolated module polish.
38. As an Ariadne maintainer, I want fallback provenance visible when LLM issue compilation fails, so that template fallback cannot masquerade as intelligent planning.
39. As an Ariadne maintainer, I want mini-code-agent dogfood to be the verification case but not a hidden implementation special case, so that the product remains general.
40. As an Ariadne maintainer, I want the PRD decomposed into vertical slices, so that each follow-up issue is independently demoable.

## Implementation Decisions

- The primary product object is Project Version. Goal is an input field of Project Version, not the runtime center.
- BuildTicket remains the work unit. Issue is a product projection of BuildTicket, not a separate persistent entity.
- The v1 dogfood target is a new mini-code-agent project advanced to v0.1.
- The mini-code-agent v0.1 target must implement a minimal coding loop, not just a README or CLI skeleton.
- The first external inputs are one GitHub repository and one blog or Markdown source.
- Source ingestion must produce typed Source Artifacts and evidence. GitHub repository analysis must include code structure, entrypoints, tests, architecture notes, reusable patterns, and risks.
- Issue generation is LLM-first with deterministic quality gates and fallback provenance. Hidden mini-code-agent templates are not allowed in the product path.
- The user must confirm Issue Delta before it becomes the Current Version Issue Set.
- The lower agent work-management layer aligns with Multica product behavior: agents, tasks, activity, skills, runtime state, assignment, and inbox are visible and backed by real data.
- Ariadne does not copy Multica's hosted technical stack. It remains local-first Python, single-user, JSON/JSONL-backed, and browser Workbench-first.
- Real Codex or Claude Code execution is mandatory for product closure. Blocked execution is allowed as diagnostic evidence, but it is not a completed phase.
- The daemon must support scoped execution of the current assignment so that Workbench users can intentionally run the selected issue.
- Handoff packets must include target project, selected issue, source evidence, constraints, allowed scope, acceptance criteria, and test command.
- Execution evidence must include stdout, stderr, exit code, changed files, diff, test result, review verdict, blockers, memory, and next issue suggestions.
- Product acceptance must be based on browser-driven Project Version Delivery closure, not CLI-only success, fake-codex, demo full, dry-run, static fixtures, or blocked rehearsal.

## Testing Decisions

- The primary test seam is Browser-driven Project Version Delivery closure.
- The highest-level acceptance path drives the Workbench browser from project/version setup through source ingestion, Issue Delta confirmation, assignment, daemon claim, real backend execution attempt, evidence return, and closure-result generation.
- The product acceptance status is `REAL_CLOSED`. `BLOCKED_WITH_EVIDENCE` is a valid diagnostic state only when an external execution dependency prevents a real run; it does not count as completion.
- Supporting tests may cover source-to-issue compilation, Issue Delta confirmation, agent task projection, runtime scoped claim, backend execution evidence capture, inbox blocker behavior, and closure evidence consistency.
- Deterministic tests must not require Codex, Claude Code, DeepSeek, Feishu, GitHub credentials, or network access unless explicitly marked as real smoke verification.
- Good tests verify external behavior and state transitions rather than implementation details. The preferred seams are Workbench/API behavior, BuildTicket projection behavior, assignment lifecycle behavior, backend execution result behavior, and closure evidence output.
- Existing dogfood, Workbench, source analysis, issue factory, agent teammate, daemon, real backend gate, inbox, and evidence tests should be reused as prior art.
- Offline regression tests may continue to use deterministic backends, but they must be labeled as offline regression and cannot satisfy the PRD acceptance.
- Browser evidence and closure-result evidence must agree on the same project version, selected issue, assignment, backend, and execution result.

## Out of Scope

- Building a hosted service, multi-tenant workspace model, auth platform, billing system, or Postgres-backed clone of Multica.
- Forking Multica or copying its technical stack.
- Pixel-perfect reproduction of Multica UI.
- Full agent marketplace, complete team builder, advanced skills editor, or multi-agent autonomy beyond the minimal v1 dogfood path.
- Full autonomous project planning without user confirmation of Issue Delta.
- Treating fake-codex, demo full, dry-run, CLI-only runs, static fixture data, or blocked rehearsal as product acceptance.
- Hardcoding mini-code-agent issue generation in the product path.
- Introducing a separate Issue persistence model outside BuildTicket projection.
- Implementing unrelated visual polish that does not reduce the Project Version Delivery friction.

## Further Notes

The main risk is scope drift back into isolated modules. Any implementation
slice must state how it reduces friction in the browser Project Version Delivery
loop. Work that adds an endpoint, page, DTO, or agent label without moving the
dogfood path closer to a real target project run is not progress for this PRD.

The next step after this PRD is to break it into tracer-bullet issues. Each issue
must cut vertically through the product path and be independently demoable.
