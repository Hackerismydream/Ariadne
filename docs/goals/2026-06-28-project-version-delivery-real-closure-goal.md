# Ariadne Goal — Project Version Delivery Real Closure

Date: 2026-06-28

This is the execution goal for closing the remaining Project Version Delivery
gap after issue #42.

## North Star

Make Ariadne prove the promised AI Builder loop in the browser:

```text
Project Version
  -> external sources
  -> issue delta
  -> current version issue set
  -> assign one current issue to a real agent
  -> daemon claims exactly that assignment
  -> real Codex or Claude modifies the target repo
  -> diff, tests, review, inbox, memory, next issues, and closure evidence
     return to Workbench
```

The target repo for the closure campaign is:

```text
/Users/martinlos/code/ariadne-dogfood/mini-code-agent
```

Completion requires a browser-produced Closure Ledger with:

```text
status: REAL_CLOSED
```

`BLOCKED_WITH_EVIDENCE` is not a successful completion state for this campaign.
If Codex or Claude cannot run because of login, quota, CLI availability,
service tier, target repo permission, or target repo git state, stop and report
the external blocker for owner intervention.

## Must Read First

Read these files in order before editing:

```text
AGENTS.md
CONTEXT.md
README.md
docs/adr/ADR-0004-ticket-centered-agent-workbench.md
docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md
docs/architecture/multica_downstream_parity_matrix.md
docs/superpowers/plans/2026-06-26-project-version-delivery-closure-phase.md
docs/architecture/project-version-delivery-closure-ledger.md
docs/runbooks/project-version-dogfood-browser-acceptance.md
```

## Current State

Already completed or in progress:

- #39: Project Version Workbench entry.
- #40: Source to Issue Delta compiler.
- #41: Apply Issue Delta into Current Version Issue Set.
- #42: Scoped issue assignment and daemon claim, pending PR #50 landing.

Remaining closure work:

- Land #50 and close #42.
- #43: Real Codex/Claude execution modifies target repo and returns evidence.
- #44: Closure evidence, review, inbox, memory, next issues, and Workbench
  progress.
- Repair `scripts/verify_dogfood_browser.sh --real` before #43 if it is stale.

## Merge Authority

Codex may auto-merge PRs during this goal only through the Merge Gate:

- PR scope matches the current issue.
- CI is green.
- Local verification is recorded.
- Browser evidence exists when product behavior changed.
- No fake/demo/mock product path is used as acceptance.
- No later-issue work is included.
- The PR comment or body states exact residual risk.

If any condition fails, do not merge.

## Execution Loop

Repeat until Closure Ledger is `REAL_CLOSED` or a real external execution
blocker requires owner intervention:

1. Refresh state:

   ```bash
   git status
   git fetch origin
   gh pr list --state open
   gh issue list --state open
   ```

2. If PR #50 is still open:

   - Review scope.
   - Confirm CI green and mergeable.
   - Confirm it implements only #42.
   - Merge it through the Merge Gate.
   - Close #42 with evidence.

3. Start from latest `main` for #43:

   ```bash
   git checkout main
   git pull origin main
   git checkout -b codex/issue-43-real-backend-target-repo-execution
   ```

4. Before implementing #43, repair the browser dogfood verifier if needed:

   ```bash
   ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 scripts/verify_dogfood_browser.sh --real
   ```

   If it fails because of stale selectors, missing UI actions, or outdated
   Workbench assumptions, fix the verifier or product path. These are Ariadne
   defects, not external blockers.

5. Implement #43:

   - Workbench must run a current-version issue through real Codex or Claude.
   - Handoff file must be inspectable from evidence.
   - The backend command must run against the dogfood target repo.
   - The target repo must have a real git diff.
   - Changed files, stdout, stderr, exit code, provider failure kind, test
     command, and test result must return to Workbench.
   - No fake-codex, dry-run, blocked rehearsal, or CLI-only success may satisfy
     #43.

6. Verify #43:

   ```bash
   python3.11 -m pytest
   ruff check .
   cd frontend/ariadne-workbench && npm run build
   ```

   Browser evidence must show the real backend execution and target repo diff.

7. Merge #43 through the Merge Gate and close #43.

8. Start #44 from latest `main`:

   ```bash
   git checkout main
   git pull origin main
   git checkout -b codex/issue-44-project-version-closure-evidence
   ```

9. Implement #44:

   - Generate Closure Ledger according to
     `docs/architecture/project-version-delivery-closure-ledger.md`.
   - Write review verdict from the real execution result.
   - Write inbox item only if there is an actionable residual blocker.
   - Write memory/outcome record.
   - Generate next issue suggestions.
   - Surface closure evidence in Workbench current version context.

10. Verify #44:

    ```bash
    python3.11 -m pytest
    ruff check .
    cd frontend/ariadne-workbench && npm run build
    ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 scripts/verify_dogfood_browser.sh --real
    ```

    Completion requires `status: REAL_CLOSED`.

11. Merge #44 through the Merge Gate and close #44.

12. Update #37 with final closure evidence and leave it open only if it still
    contains product work beyond this closure campaign.

## Hard Stop Conditions

Stop and report, do not work around, when any of these external blockers occurs:

- Codex CLI unavailable.
- Claude CLI unavailable.
- Required backend not logged in.
- Quota or rate limit prevents real code modification.
- Invalid Codex/Claude config such as unsupported service tier.
- Dogfood target repo cannot be safely edited because of permissions or git
  state.

Do not stop for Ariadne defects. Fix Ariadne defects:

- stale browser selector;
- missing button action;
- source not analyzed;
- issue not generated;
- handoff empty;
- daemon claims wrong assignment;
- evidence not returned to Workbench;
- closure ledger missing fields.

## Non-Goals

- Do not build a hosted service.
- Do not introduce Go, Postgres, auth, workspace billing, or a Multica clone.
- Do not add independent Issue persistence.
- Do not use Ariadne's own repo as the dogfood target.
- Do not ship visual polish that does not reduce the Project Version Delivery
  gap.
- Do not use fake-codex, demo full, dry-run, or CLI-only evidence as closure.

## Final Goal Prompt

Copy this block into a long-running Codex goal thread:

```markdown
Continue Ariadne Project Version Delivery Real Closure.

Workspace: /Users/martinlos/code/Ariadne
Repository: https://github.com/Hackerismydream/Ariadne

Read first, in order:

AGENTS.md
CONTEXT.md
README.md
docs/adr/ADR-0004-ticket-centered-agent-workbench.md
docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md
docs/architecture/multica_downstream_parity_matrix.md
docs/superpowers/plans/2026-06-26-project-version-delivery-closure-phase.md
docs/architecture/project-version-delivery-closure-ledger.md
docs/runbooks/project-version-dogfood-browser-acceptance.md
docs/goals/2026-06-28-project-version-delivery-real-closure-goal.md

Goal:
Deliver browser-proven REAL_CLOSED Project Version Delivery for the dogfood
target repo /Users/martinlos/code/ariadne-dogfood/mini-code-agent.

Execution authority:
- You may review, commit, push, create PRs, merge PRs, and close issues only
  when the Merge Gate in CONTEXT.md and the goal document passes.
- Do not merge if scope leaks, CI fails, browser evidence is missing, product
  path uses fake/demo/mock data, or later-issue work is included.

Current sequence:
1. Review/merge PR #50 if still open; close #42 with evidence.
2. From latest main, implement #43.
3. Before #43, repair scripts/verify_dogfood_browser.sh --real if stale.
4. #43 is complete only when real Codex or Claude successfully modifies the
   dogfood target repo and Workbench receives stdout/stderr/exit code, changed
   files, git diff, test result, and execution evidence.
5. Merge #43 through the Merge Gate and close #43.
6. From latest main, implement #44.
7. #44 is complete only when review, inbox, memory, next issues, Workbench
   progress, and closure-result.json are produced.
8. Run ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 scripts/verify_dogfood_browser.sh --real.
9. Final completion requires closure ledger status REAL_CLOSED.

Hard rule:
BLOCKED_WITH_EVIDENCE is not completion for this campaign. External execution
blockers stop the goal and require owner intervention. Ariadne defects must be
fixed, not classified as external blockers.

Verification for each implementation PR:
python3.11 -m pytest
ruff check .
cd frontend/ariadne-workbench && npm run build
browser Workbench evidence for the changed product path

Never use fake-codex, demo full, dry-run, static fixture, mock data, or CLI-only
success as product closure.
```

