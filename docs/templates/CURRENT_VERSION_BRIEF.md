# Current Version Brief

Use this brief at the start and end of each Ariadne delivery turn. It is the
single page for the current project version, not a historical ticket archive.

## Version Identity

- Date:
- Owner:
- Branch:
- Commit:
- Target project:
- Target version:
- Product mode: `fixture | local-real | external-real`
- Status: `draft | ready_for_execution | running | blocked | closed | shipped`

## Version Goal

- User-facing goal:
- Non-goals:
- Why this version matters now:
- Definition of done:

## Product Boundary

- Ariadne shape: `local-first single-user CLI/workbench`
- Persistence boundary:
- Runtime boundary:
- External systems:
- Explicitly out of scope:

## Inputs And Understanding

| Source | Type | Fetch status | Artifact | Evidence refs | Notes |
| --- | --- | --- | --- | --- | --- |
|  |  | `analyzed | partial | blocked` |  |  |  |

Required checks:

- [ ] Every selected source has a `SourceFetchRecord` or explicit blocked record.
- [ ] Every analyzed source has typed artifacts, not just raw text.
- [ ] The issue compiler consumes a frozen `BuildContextManifest`.
- [ ] User-visible summary explains what was understood and what happens next.

## Current Issue Set

| Issue | State | Source evidence | Affected modules | Acceptance criteria | Version role |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  | `mainline | repair | follow-up | out-of-scope` |

Issue hygiene:

- [ ] Historical repair issues are hidden or explicitly marked as historical.
- [ ] Current mainline issue is visible without reading old blocker history.
- [ ] Acceptance criteria are testable.
- [ ] No issue is claimable without source evidence.

## Route, Handoff, Assignment

- Route decision:
- Handoff packet:
- Assignment:
- Assigned runtime:
- Runtime authorization:
- Claim readiness: `not_ready | ready_to_claim | claimed | terminal`

Readiness checks:

- [ ] Route decision is persisted.
- [ ] Handoff packet is frozen.
- [ ] Assignment references route and handoff ids.
- [ ] Assignment includes source evidence and acceptance criteria.
- [ ] Runtime consumes the frozen handoff instead of rebuilding a conflicting prompt.

## Execution Evidence

| Run | Backend | Session | Exit code | Changed files | Artifact path |
| --- | --- | --- | --- | --- | --- |
|  | `codex | claude | fake-codex | dry-run` |  |  |  |  |

Evidence quality:

- [ ] Real acceptance evidence is separated from fixture or dry-run evidence.
- [ ] Changed target files are listed concretely.
- [ ] Stale or superseded failed attempts do not override current terminal proof.
- [ ] Evidence path is reproducible from the repo root.

## Verification Gates

| Gate | Command | Result | Artifact |
| --- | --- | --- | --- |
| Static checks | `ruff check .` |  |  |
| Unit tests | `python3.11 -m pytest` |  |  |
| CLI demo | `python3.11 -m ariadne_ltb.cli demo full` |  |  |
| Board export | `python3.11 -m ariadne_ltb.cli export board` |  |  |
| Workbench QA |  |  |  |

Gate policy:

- [ ] Failing gates are recorded as blockers, not hidden.
- [ ] Fixture gates are not described as production acceptance.
- [ ] External-real gates name required env vars and confirmations.

## Blockers And Recovery

| Blocker | Layer | Evidence | Recovery action | Owner | Status |
| --- | --- | --- | --- | --- | --- |
|  | `source | compiler | route | handoff | runtime | review | UI | external` |  |  |  |  |

Blocker policy:

- [ ] External dependency failures are labeled as external blockers.
- [ ] Local product failures become repair issues only if they affect current closure.
- [ ] Recovery action has a concrete next command or code owner.

## Review, Memory, And Follow-Up

- Review verdict:
- Review artifact:
- Memory artifact:
- Feishu or external write plan:
- Next tickets artifact:

Follow-up rules:

- [ ] Follow-ups are split into mainline continuation, repair, and later cleanup.
- [ ] Reusable decisions are written to memory or docs.
- [ ] User-facing summary states what shipped, what did not, and why.

## Release Status

- Closure status: `not_started | blocked | real_closed | shipped`
- Release branch:
- Commit:
- Push status:
- Demo readiness:
- Known limitations:

## Final Report Stub

- What changed:
- Why this shape:
- Evidence:
- Verification:
- Blockers or limitations:
- Next version:
