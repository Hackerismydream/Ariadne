# Review, Memory, and Next Tickets

## Reviewer

The reviewer must check the real ticket run result.

Required checks:

- Build Packet exists;
- evidence exists;
- project relevance exists;
- acceptance criteria exist;
- handoff artifact exists;
- execution result exists;
- backend not blocked unless expected;
- exit code is 0;
- test exit code is 0 if tests were requested;
- changed files are captured;
- changed files are within allowed scope;
- git diff exists if git is available;
- all Agent Runs are terminal;
- Feishu plan is dry-run unless explicitly confirmed.

## Verdicts

```text
pass
needs_fix
blocked
needs_human_review
```

Status mapping:

```text
pass -> done
needs_fix -> needs_fix
blocked -> blocked
needs_human_review -> waiting_approval
```

## Memory

The common `ticket run` command must write memory automatically.

Required memory outputs:

```text
.ariadne/memory/tickets/<ticket_id>.md
.ariadne/memory/tickets/<ticket_id>.json
.ariadne/memory/build_packets/<packet_id>.json
.ariadne/memory/reviews/<ticket_id>.md
.ariadne/memory/decision_log.md
.ariadne/memory/weekly_summary.md
```

## Feishu dry-run

Generate Feishu dry-run plan automatically.

Required file:

```text
.ariadne/feishu_plans/<plan_id>.json
```

It must remain dry-run unless both env flag and CLI confirmation are present.

## Next Ticket Generator

This is required for the loop.

Add a generator that creates next ticket suggestions from review/memory.

Output:

```text
.ariadne/artifacts/<ticket_id>/next_tickets.json
```

or:

```text
.ariadne/artifacts/<ticket_id>/next_tickets.md
```

Suggested next tickets may include:

- improve retrieval over local memory;
- add real Codex backend smoke test;
- upgrade Feishu write-back to docs + tasks;
- build FastAPI board;
- add Build Packet quality evaluator.

But do not just hard-code a static report. Base suggestions on:

- review verdict;
- failed checks;
- changed files;
- source type;
- current ticket decision;
- memory gaps.

## Loop story

The end of each ticket run should create the inputs for the next run:

```text
review result -> memory -> next tickets -> future Codex work
```
