# Ariadne Maturity Issue Pack

Generated: 2026-06-20 Asia/Shanghai  
Branch: `codex/ariadne-maturity-campaign`  
Repository: `Hackerismydream/Ariadne`

## Scope

This pack tracks only issues that directly improve Ariadne as a local-first,
single-user, ticket-centered Agent Workbench. It intentionally rejects
hosted-service rewrites, Postgres/auth migrations, Multica cloning, and
stale-doc-only cleanup.

## Audit Snapshot

- Worktree branch: `codex/ariadne-maturity-campaign`.
- Open GitHub issues before audit: none.
- Open GitHub PRs before audit:
  - PR #15: `codex/real-source-to-agent-compiler-plan` -> `main`
    (`Plan real source-to-agent compiler`), mergeable at audit time.
- `python3.11 -m ariadne_ltb.cli backend doctor`: passed, redacted local
  secret finding in `.env`.
- `python3.11 -m ariadne_ltb.cli doctor product`: initially crashed on a
  legacy `landing_gate` artifact type in the local artifact index. This became
  the first P0 maturity issue.
- Focused product tests before the first fix:
  - `tests/test_frontend_api_contract_static.py`
  - `tests/test_cli_product_defaults.py`
  - `tests/test_source_repository_fetch.py`
  - `tests/test_repository_scanner.py`
  - `tests/test_handoff_packet_readiness.py`
  - Result: `28 passed`.

## Reviewed Issue List

### MAT-001: Product doctor must tolerate legacy artifact types

- GitHub: https://github.com/Hackerismydream/Ariadne/issues/16
- Priority: P0
- Labels: `bug`, `maturity-campaign`, `priority:P0`, `area:doctor`
- Status: implemented in this branch, pending commit/push evidence.
- Problem: `ari doctor product` must report readiness even when old local
  artifact records contain unknown legacy enum values such as
  `artifact_type=landing_gate`.
- Acceptance:
  - Legacy/unknown artifact types do not crash product doctor.
  - Invalid legacy artifacts do not count as success evidence.
  - Regression test covers the legacy `landing_gate` case.
  - `product_readiness.json` is still written.

### MAT-002: Workbench must show daemon execution feedback end to end

- GitHub: https://github.com/Hackerismydream/Ariadne/issues/17
- Priority: P0
- Labels: `enhancement`, `maturity-campaign`, `priority:P0`,
  `area:workbench`, `area:runtime`
- Status: in progress.
- Problem: the browser product must show assignment dispatch, daemon claim,
  execution result, diff, tests, review, memory, and next actions without
  requiring CLI inspection.
- Acceptance:
  - User can assign a ticket from Workbench.
  - Local daemon claims and records lifecycle events.
  - Issue page displays execution result id, exit code, changed files, test
    result, reviewer verdict, memory path, and next-ticket path.
  - Blocked execution appears as typed blocked result in the page.
  - Browser QA proves local API usage, not static fixtures.
- 2026-06-20 slice:
  - `AgentRun` now records `assignment_id` and `runtime_id` metadata.
  - Assignment event streams now include same-assignment artifact events for
    execution log, diff, changed files, tests, review, memory, Feishu plan, and
    next tickets.
  - Workbench refreshes its snapshot when WebSocket/HTTP assignment events
    include artifact/result/blocker/done signals.

### MAT-003: Product readiness needs guided release evidence regeneration

- GitHub: https://github.com/Hackerismydream/Ariadne/issues/18
- Priority: P1
- Labels: `enhancement`, `maturity-campaign`, `priority:P1`, `area:doctor`,
  `area:integrations`
- Status: completed on `codex/ariadne-maturity-campaign`.
- Problem: release evidence can be missing or stale, leaving product readiness
  blocked without a guided regeneration path.
- Implementation:
  - Release evidence packets now persist readiness next actions, blocking
    checks, stale status, and stale reasons.
  - Product doctor now separates missing packet, missing integration refs,
    stale packet, missing real evidence, and unset run gates.
  - `ari evidence packet` table output shows stale state and the top next
    actions.
  - The Workbench release evidence panel exposes the same readiness summary in
    Chinese, including `下一步`, `证据过期`, and stale reasons.
- Acceptance:
  - Done: `ari evidence packet` can be regenerated after current product runs.
  - Done: product doctor separates missing packet, missing refs, stale packet,
    missing real
    evidence, and unset run gates.
  - Done: Workbench exposes the same readiness summary in Chinese.
  - Done: tests cover stale/missing packet behavior.

### MAT-004: Add auditable DeepSeek LLM agent proof flow

- GitHub: https://github.com/Hackerismydream/Ariadne/issues/19
- Priority: P1
- Labels: `enhancement`, `maturity-campaign`, `priority:P1`,
  `area:integrations`
- Status: completed on `codex/ariadne-maturity-campaign`.
- Problem: product doctor can require LLM role evidence, but there is no
  bounded proof flow for Build Lead, Knowledge, Memory, planner, reviewer, and
  backlog agents.
- Implementation:
  - Added `ari llm proof --ticket <ticket> --confirm-external`.
  - The proof command requires an existing ticket execution result before
    running reviewer/backlog proof so Ariadne does not fabricate inputs.
  - The proof sequence runs Build Lead, Knowledge, Memory, LLM planner, LLM
    reviewer, and LLM backlog planning for one ticket.
  - The command writes a redacted proof artifact and each sub-operation writes
    its normal provider/model/ticket evidence.
  - Real DeepSeek proof was run for `ARI-003`; all six operations succeeded and
    product doctor reported `real_llm_agent_evidence: ready`.
- Acceptance:
  - Done: one command runs the required LLM proof sequence for
    one ticket behind explicit external-confirmation gates.
  - Done: artifacts persist provider/model/ticket metadata and redacted
    failures.
  - Done: product doctor consumes those artifacts.
  - Done: tests cover no-key blocked path and recorded-success path without
    network.

### MAT-005: Make inbox blockers actionable from Workbench

- GitHub: https://github.com/Hackerismydream/Ariadne/issues/20
- Priority: P1
- Labels: `enhancement`, `maturity-campaign`, `priority:P1`,
  `area:workbench`
- Status: open.
- Problem: blockers are visible, but users need direct repair, rerun,
  acknowledge, and evidence actions.
- Acceptance:
  - Workbench inbox supports create repair issue, rerun linked assignment,
    acknowledge/resolve, and evidence view.
  - Backend APIs enforce typed failure reasons and avoid duplicate repair spam.
  - Repair actions append comments/events to the source ticket.
  - Tests cover API actions and frontend contract.

### MAT-006: Reconcile real source-to-agent compiler PR into maturity baseline

- GitHub: https://github.com/Hackerismydream/Ariadne/issues/21
- Priority: P1
- Labels: `enhancement`, `maturity-campaign`, `priority:P1`,
  `area:workbench`
- Status: completed on `codex/ariadne-maturity-campaign`.
- Problem: source-to-agent compiler work exists on PR #15 and must be
  reconciled with the maturity baseline before dependent product work builds on
  divergent branches.
- Reconciliation decision:
  - PR #15 is superseded by the maturity campaign branch for landing purposes.
  - The maturity branch contains PR #15 commit
    `911516f feat: implement real source-to-agent compiler` as an ancestor.
  - Future product work should target `codex/ariadne-maturity-campaign`, not
    `codex/real-source-to-agent-compiler-plan`, so source compiler, product
    doctor, and Workbench evidence changes stay in one reviewed baseline.
- Evidence:
  - `git merge-base --is-ancestor 911516f HEAD` returned `0` on
    `codex/ariadne-maturity-campaign`.
  - `git branch --contains 911516f` listed both
    `codex/ariadne-maturity-campaign` and
    `codex/real-source-to-agent-compiler-plan`.
  - Browser QA for the source compiler slice is recorded in
    `docs/development_report.md`: adding `https://github.com/e10nMa2k/cc-mini`
    auto-filled the repo title, completed source analysis, and rendered
    repository understanding evidence.
- Acceptance:
  - Done: PR #15 is documented as superseded by the maturity campaign branch.
  - Done: the maturity baseline has real source fetch/cache, repository
    understanding, typed issue compiler, and frozen handoff behavior.
  - Done: browser QA covers adding a GitHub repo URL and seeing repository
    understanding evidence.
  - Done: branch/PR decision is documented before close.

## Deduplication Decisions

- Stale roadmap wording without runtime/product impact was not converted into
  issues.
- Hosted service, Postgres, multi-tenant auth, and Multica-clone work were
  rejected for v1.x.
- Fake/demo/offline regression cleanup is only tracked when it affects product
  readiness or user-facing evidence.
- The first implementation slice is MAT-001 because it blocked product health
  inspection itself.

## Next Candidate

After MAT-001, MAT-002, and MAT-006, the next highest-value issue is MAT-003.
It should make release evidence regeneration guided and auditable so product
readiness blockers are actionable instead of only descriptive.
