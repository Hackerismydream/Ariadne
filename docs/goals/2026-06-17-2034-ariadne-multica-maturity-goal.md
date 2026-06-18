# Goal: 2026-06-17-2034 Ariadne Multica Maturity

Status: superseded

Superseded by:

```text
docs/goals/2026-06-17-2043-ariadne-production-agent-workbench-goal.md
```

Reason: this goal was too conservative for the current product direction. The
active goal is production-first and requires real DeepSeek, Codex, Claude Code,
Feishu, and GitHub integrations where configured.

You are Codex working on Ariadne.

Your objective is to drive Ariadne toward Multica-level local agent
work-management maturity.

Read and follow this detailed execution plan first:

```text
docs/superpowers/plans/2026-06-17-2034-ariadne-multica-maturity-execution-plan.md
```

Also treat these files as authoritative context:

```text
docs/ops/ARIADNE_MULTICA_MATURITY_ROADMAP.md
docs/adr/ADR-0004-ticket-centered-agent-workbench.md
docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md
docs/ops/CODEX_NON_FRONTEND_SECTION_PLAN.md
docs/architecture/multica_architecture_digest.md
docs/architecture/ariadne_multica_gap_report.md
```

North star:

```text
Ariadne = local-first Ticket-centered Agent Workbench

Knowledge / Feedback / Codebase / optional Goal
  -> update Ticket backlog
  -> Ticket management center
  -> assign to Agent
  -> local Daemon / Runtime
  -> Codex / Claude / fake-codex
  -> Review / Comments / Board / Memory
  -> update Ticket backlog again
```

Goal can be input context. Goal is not the runtime center. Build Ticket is the
work center, audit center, assignment center, review center, and board center.

Do not turn Ariadne into a Multica fork. Keep Ariadne Python, local-first,
single-user, JSON/JSONL-backed, deterministic, and safety-gated.

Your first responsibility is branch and roadmap discipline:

1. Re-check current branch state before editing.
2. Do not independently merge stale feature branches into `main`.
3. Decide when the existing frontend/demo branch should be integrated, based on
   the detailed plan and current conflicts.
4. Do not develop new frontend features in this goal. Frontend work is allowed
   only when resolving integration conflicts or exposing stable backend data
   contracts needed by the existing frontend branch.

Then implement the roadmap in small, independently mergeable slices:

1. integrate current core and frontend branch state when safe;
2. resource boundaries and execution safety;
3. inbox, blocker handling, and local search;
4. review/eval and acceptance quality;
5. session/workdir reuse, cleanup, and store durability;
6. board, CLI, and existing web workbench parity;
7. dogfood scenario and release evidence.

For every code slice:

```text
inspect current code
declare owned files
implement minimal vertical change
add or update tests
run verification
commit
push
write Chinese progress evidence
```

Required verification for non-doc code:

```bash
python3.11 -m pytest
python3.11 -m ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
scripts/verify_v1.sh
```

For integration involving the existing frontend branch, also run:

```bash
npm --prefix frontend/ariadne-workbench run build
```

Do not claim real Codex, Claude, Feishu, GitHub, or external execution worked
unless it actually ran and the result is recorded.

Stop only for true blockers: unsafe external state, contradictory product
direction, unresolvable merge conflict, missing credentials required for an
explicitly requested real external action, or repeated verification failure
after evidence-backed repair attempts.
