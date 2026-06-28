# Project Version Dogfood Browser Acceptance Runbook

Date: 2026-06-28

## Purpose

This runbook defines the only accepted end-to-end product verification for the
current closure campaign.

The verification command is:

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 scripts/verify_dogfood_browser.sh --real
```

For this campaign, the command must finish with:

```text
status: REAL_CLOSED
```

## Preflight

Run from the Ariadne repository:

```bash
cd /Users/martinlos/code/Ariadne
git status
python3.11 -m pytest
ruff check .
cd frontend/ariadne-workbench && npm run build
cd ../..
```

Verify the dogfood target repo exists:

```bash
test -d /Users/martinlos/code/ariadne-dogfood/mini-code-agent
git -C /Users/martinlos/code/ariadne-dogfood/mini-code-agent status
```

Verify real backend availability:

```bash
codex --version || true
claude --version || true
python3.11 -m ariadne_ltb.cli backend doctor
```

If Codex/Claude is not logged in, quota is exhausted, or service tier config is
invalid, stop and ask the owner to fix the external state. Do not switch to
fake-codex or dry-run.

## Browser Flow

The verifier must drive Workbench as a user:

1. Start Workbench:

   ```bash
   python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8766
   ```

2. Open:

   ```text
   http://127.0.0.1:8766/
   ```

3. Create or select a Project Version for:

   ```text
   Target repo: /Users/martinlos/code/ariadne-dogfood/mini-code-agent
   Target version: v0.1
   Goal: build a minimal coding agent from external source understanding
   ```

4. Add external sources in the Sources page. At minimum use one GitHub repo or
   markdown source that can produce target-project evidence.

5. Generate Issue Delta from Plan Changes.

6. Apply the Issue Delta.

7. Open Issues and select one current-version issue.

8. Assign it to a real Codex or Claude agent.

9. Start daemon scoped to that assignment.

10. Confirm real backend execution changes the dogfood target repo.

11. Confirm Workbench receives:

    - handoff path;
    - stdout/stderr/exit code;
    - changed files;
    - git diff;
    - test command and result;
    - review verdict;
    - inbox state;
    - memory/outcome record;
    - next issue suggestions;
    - current version progress.

12. Confirm `closure-result.json` status is `REAL_CLOSED`.

## Pass Criteria

Pass only when the Closure Ledger satisfies
`docs/architecture/project-version-delivery-closure-ledger.md` and includes:

- real Codex or Claude backend;
- target repo code change;
- non-empty changed files;
- diff artifact;
- test result;
- review verdict;
- Workbench evidence;
- current project/version identity;
- source evidence lineage.

## Failures That Must Be Fixed

These are Ariadne defects:

- stale selector in the verifier;
- page route changed without verifier update;
- button exists but has no real API action;
- source is saved but not analyzed;
- issue delta is generated but cannot apply;
- Issues board shows history instead of current-version issues;
- assignment created but daemon claims a different task;
- handoff file is empty or not inspectable;
- execution artifacts do not return to Workbench;
- closure ledger is missing required fields.

## External Blockers

These stop the goal and require owner intervention:

- Codex CLI unavailable or not logged in;
- Claude CLI unavailable or not logged in;
- quota or rate limit prevents code modification;
- invalid Codex/Claude service tier config;
- target repo permission or git state blocks safe editing.

Do not convert these into success. Record the blocker, stop, and ask the owner
to fix the external state.

## Evidence Directory

Each verifier run writes to:

```text
.ariadne/dogfood/browser-<timestamp>/
```

For PR review, copy or link the essential evidence into:

```text
docs/evidence/<issue-or-campaign>/
```

Minimum PR evidence:

- `closure-result.json`;
- browser screenshots;
- Workbench API snapshots;
- target repo `git status` before/after;
- target repo diff artifact;
- test output;
- review report.

## What Not To Do

- Do not use `ari demo full`.
- Do not use fake-codex.
- Do not call internal APIs instead of browser actions.
- Do not edit `.ariadne` JSON files manually to create success.
- Do not use Ariadne repository as the target repo.
- Do not claim `BLOCKED_WITH_EVIDENCE` as campaign completion.

