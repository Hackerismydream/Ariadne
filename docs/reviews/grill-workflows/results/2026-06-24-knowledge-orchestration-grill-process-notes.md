# Knowledge Orchestration Grill Process Notes

This file records the five-round grill process required by
`2026-06-24-knowledge-orchestration-grill-workflow.md`.

## Evidence Baseline

- Browser screenshots:
  - `docs/reviews/grill-workflows/results/2026-06-24-knowledge-sources.png`
  - `docs/reviews/grill-workflows/results/2026-06-24-knowledge-plan-changes.png`
  - `docs/reviews/grill-workflows/results/2026-06-24-knowledge-issues.png`
- Browser `#sources`: 61 sources, 9 ready, many queued; visible source lane mixes review feedback, blogs, GitHub repos, task-title sources.
- Browser `#plan-changes`: latest visible delta is `backlog_preview_d28c447255c1`, including `未命名任务` with 0 artifacts, 0 evidence refs, 0 acceptance criteria, 0 affected modules.
- Browser `#issues`: 10 current issues; 9 backlog cards show `0 evidence`; `M0TR-003` is blocked.
- API `/api/workbench`: `sources=61`, `sourceArtifacts=9`, `sourceEvidence=9`, `projectInputs=61`, `tickets=10`.
- Persisted M0TR tickets: each `M0TR-001..010` has 9 evidence refs, 9 source artifact ids, 9 source document ids, affected modules, 3 acceptance criteria.
- Original source-generated preview: `backlog_preview_8aa11cc0eca5`, trigger `manual_goal`, 10 grounded operations.
- Latest visible Plan Changes preview: `backlog_preview_d28c447255c1`, trigger `review_feedback`, ungrounded repair/follow-up operations.
- Build context `build_context_825e3a5124d7`: source/artifact/evidence ids present, `codebase_snapshot_artifact_id=null`.
- `.ariadne/knowledge/resource_56a27abf28d0/`: only `outcomes_log.json` and one `blocker_learnings/*.json`; no `source_insights` or `synthesis_themes`.

## Round 1

### Candidate Generator

1. B1-1: Why can a user add 61 sources but only 9 become ready without a clear product-level queue, prioritization, or next action?
2. B1-2: Why does the source list mix external knowledge, review feedback, and generated task-title sources in one flat lane, making the source-to-issue lineage unclear?
3. B1-3: Why does Plan Changes show an applied delta item named `未命名任务` with 0 artifacts, 0 evidence refs, and 0 acceptance criteria?
4. B1-4: Why do 9 of 10 current issues show 0 evidence if issues are supposed to be grounded in external knowledge and ProjectKnowledge?
5. B1-5: Why does Current Version Context mark Sources readiness and Issue Delta done while most sources remain pending and most issues lack evidence?
6. B1-6: Why is the user expected to infer that `Go to Plan Changes` is the next step instead of Ariadne narrating source analysis -> knowledge -> issue delta lineage?
7. B1-7: Why does the Workbench not expose ProjectKnowledge artifacts even though Phase 8 made ProjectKnowledge the middle layer?
8. B1-8: Why are source titles often task titles such as `Capture git diff and test result`, suggesting issue output has leaked back into source input?
9. B1-9: Why does the current browser dogfood evidence prove a blocked runtime issue but not source-to-ticket reasoning quality?

### Four Independent Reviewer Outputs

#### Reviewer 1: AI Builder User

- Keep: B1-1, B1-2, B1-3, B1-4, B1-5, B1-8, B1-9.
- Drop: B1-7 as written because raw ProjectKnowledge HTTP exposure is outside Phase 8.
- Merge / Rewrite: merge B1-6 into B1-1/B1-5; rewrite B1-7 as missing user-readable knowledge-to-issue explanation.
- New questions: lifecycle visibility after paste; raw input vs derived artifact separation; issue-to-source trace; next action when sources queued but issue delta done.
- Evidence: browser/API baseline; `SourcesPage.tsx` next action is mostly `Go to Plan Changes`; `PlanChangesPage.tsx` can render empty artifacts/evidence.

#### Reviewer 2: Knowledge Agent Engineer

- Keep: B1-3, B1-4, B1-5, sharpened B1-7, B1-8.
- Drop: B1-6, B1-9 as standalone.
- Merge / Rewrite: B1-1+B1-6 into typed source-analysis queue; B1-2+B1-8 into source lane contamination; B1-7 into allowed projection of SourceInsight/SynthesisTheme evidence.
- New questions: why live knowledge state lacks source insights/themes; whether 9 ready artifacts became ProjectKnowledge; synthetic SourceDocument leakage; API artifact/evidence mismatch; stable trace path.
- Evidence: `.ariadne/knowledge` lacks source insight/theme files; `issue_factory.py` creates synthetic task-derived source documents; fallback path can bypass ProjectKnowledge.

#### Reviewer 3: Issue Factory Reviewer

- Keep: B1-3, B1-4, B1-8, B1-5, B1-9.
- Drop: B1-6 and B1-7 as phrased.
- Merge / Rewrite: B1-2+B1-8 as synthetic-source lineage; B1-1+B1-5 as truthfulness of done/readiness; B1-3 asks whether preview is ProjectKnowledge, fallback, stale projection, or UI mapping loss; B1-4+B1-9 asks whether dogfood proves grounding.
- New questions: persisted metadata per issue; whether 0 fields are data loss or projection loss; compile path used; missing target codebase snapshot; why M0TR prefix diverges from MCA dogfood expectation.
- Evidence: issue factory writes evidence/criteria/modules into operation metadata; old deterministic compiler has fixed mini-code-agent tasks.

#### Reviewer 4: Handoff And Dogfood Reviewer

- Keep: B1-3, B1-4, B1-5, B1-8, B1-9.
- Drop: B1-7 as raw ProjectKnowledge exposure.
- Merge / Rewrite: B1-1+B1-2+B1-6 into visible source lifecycle for handoff readiness; rewrite B1-3 as empty delta reaching handoff surface.
- New questions: which fields may be empty before assignment; whether current handoffs are meaningful for 0 evidence issues; target-repo execution evidence; current issue scoping; end-to-end trace to handoff/run.
- Evidence: `handoff_packets.py` depends on affected modules, acceptance criteria, test command, evidence refs; dogfood doc requires visible build packet/handoff/execution/review/memory/next issue evidence.

### Judge Scoring And Merge Decision

- B1-3: 25/25, keep P0.
- B1-4: 25/25, keep P0.
- B1-5: 23/25, keep P0.
- B1-2+B1-8: 22/25, merge and keep.
- B1-1+B1-6: 20/25, merge and keep.
- B1-7: 18/25 after rewrite, keep as "missing user-readable knowledge grounding", not raw API exposure.
- B1-9: 18/25, keep as dogfood evidence gap.

### Round Ledger

#### Keep

- Empty applied Plan Changes item invalidates issue-delta trust.
- Evidence missing from issue UI invalidates source-grounding trust.
- Current Version Context has misleading readiness/done states.
- Source lane is polluted by derived/generated task-title sources.
- Dogfood only proves blocked runtime visibility, not knowledge-to-work quality.

#### Drop

- Raw ProjectKnowledge API exposure as a requirement; Phase 8 forbids it.

#### Merge

- Source queue + next action + lifecycle narration merged.
- Mixed source lane + task-title source leakage merged.
- ProjectKnowledge exposure rewritten as allowed user-readable lineage through source artifacts / issue evidence / handoff evidence.

#### Remaining Gaps

- Determine whether 0 evidence is real missing data or projection loss.
- Determine whether Plan Changes is selecting the wrong preview.
- Determine whether ProjectKnowledge was used or fallback templates were used.

#### Next Focus

Root-cause the data/projection/fallback split.

## Round 2

### Candidate Generator

1. B2-1: Why does the issue projection display 0 evidence when persisted BuildTicket metadata contains evidence_refs/source_artifact_ids/source_document_ids?
2. B2-2: Why does Plan Changes default to the latest review-feedback repair preview instead of the current version's original source-to-issue delta?
3. B2-3: Why can review-feedback operations with title=None and no grounding metadata render as applied Issue Delta items instead of repair/inbox changes?
4. B2-4: Why is current version context counting issue delta as applied without distinguishing source-generated mainline delta from feedback-generated repair delta?
5. B2-5: Why did Phase 8 ProjectKnowledge not persist SourceInsight/SynthesisTheme files for the current build context despite source-to-issue generation having occurred?
6. B2-6: Why does the BuildContextManifest for the current issue set have codebase_snapshot_artifact_id=null if Issue Factory is supposed to use current target codebase state?
7. B2-7: Why is evidence lineage stored in metadata but not reliably surfaced in browser issue cards, issue detail, and Plan Changes selected delta?
8. B2-8: Why are repair tickets ARI-074..076 generated with no affected modules, acceptance criteria, or evidence, making them weak follow-up work?
9. B2-9: Why does the product lack a clear distinction between mainline issue set, repair issue suggestions, review feedback deltas, and historical previews?

### Four Independent Reviewer Outputs

#### Reviewer 1: AI Builder User

- Keep: B2-1, B2-2, B2-3, B2-4, B2-7, B2-8, B2-9.
- Drop: B2-5 and B2-6 as implementation details unless rewritten into user-visible source understanding/codebase grounding.
- Merge / Rewrite: B2-1+B2-7 into evidence persisted but hidden; B2-2+B2-4+B2-9 into collapsed preview taxonomy; B2-3+B2-8 into ungrounded next actions.
- New questions: authoritative source of truth; Plan Changes default selection rule; distinguish source issue vs review feedback; prevent empty repair tickets; separate statuses in Current Version Context.

#### Reviewer 2: Knowledge Agent Engineer

- Keep: B2-1, B2-2, B2-3, B2-4, B2-5, B2-6, B2-7, B2-9.
- Drop: B2-8 as standalone.
- Merge / Rewrite: B2-1+B2-7; B2-2+B2-4+B2-9; B2-3+B2-8; B2-5 focused on build context lacking SourceInsight/SynthesisTheme.
- New questions: authoritative selector for current mainline delta; projection reading metadata; invariant against repair preview replacement; codebase snapshot null; disclose deterministic fallback.

#### Reviewer 3: Issue Factory Reviewer

- Keep: B2-1, B2-2, B2-3, B2-5, B2-6, B2-9.
- Drop: B2-7 duplicate, B2-4 standalone, B2-8 standalone.
- Merge / Rewrite: B2-1+B2-7; B2-2+B2-3+B2-4+B2-9; B2-5+B2-6.
- New questions: projection function for evidence count; current Plan Changes preview selection rule; review-feedback mutation semantics; proof Phase 8 ingest ran; target codebase snapshot creation.

#### Reviewer 4: Handoff And Dogfood Reviewer

- Keep: B2-1, B2-2, B2-3, B2-4, B2-6, B2-7, B2-8, B2-9.
- Drop: none.
- Merge / Rewrite: B2-2+B2-4+B2-9; B2-5 rewritten as fallback disclosure; B2-1+B2-7 if fewer questions needed.
- New questions: validate handoff fields before assignment; issue detail shows persisted refs; handoff packet includes readable evidence; empty repair tickets reaching execution; target repo state warning.

### Judge Scoring And Merge Decision

- B2-1/B2-7: 25/25, merge as projection evidence loss.
- B2-2/B2-4/B2-9: 25/25, merge as preview taxonomy/current delta selection failure.
- B2-3/B2-8: 23/25, merge as ungrounded repair delta rendering/execution risk.
- B2-5: 23/25, keep as Phase 8 ProjectKnowledge not proven.
- B2-6: 21/25, keep as codebase grounding missing.

### Round Ledger

#### Keep

- Persisted evidence exists but is hidden by issue projection.
- Plan Changes selects the wrong preview class.
- Review-feedback operations with no title/metadata become issue-delta work.
- ProjectKnowledge files are absent for source reasoning.
- Codebase snapshot is absent from build context.

#### Drop

- Duplicative B2-7 as separate from B2-1.
- Repair ticket quality as standalone only; keep it inside ungrounded repair delta issue.

#### Merge

- Evidence projection loss.
- Preview taxonomy collapse.
- Ungrounded repair/feedback work rendering.

#### Remaining Gaps

- Source artifacts may be low quality even when present.
- Repo understanding may be README-level.
- Handoffs may cite IDs but not readable evidence.

#### Next Focus

Evaluate source/repo understanding quality and handoff evidence readability.

## Evidence Correction After Round 4

An initial `jq` check queried root fields from `GET /api/issues/M0TR-003`.
The API response wraps detail data under `.issue`; therefore issue detail lookup
by key is not proven broken. The corrected evidence is:

- `GET /api/issues/M0TR-003 | jq .issue` returns a detail object.
- `M0TR-003` detail has `evidence_count=24`, source links, handoff, execution, review, test, and diff summaries.
- `M0TR-001` detail has source links but `evidence_count=0`, `acceptance_criteria=null`, `affected_modules=null`, no assignment, and no handoff.
- Persisted `M0TR-001` BuildTicket metadata contains evidence refs, affected modules, and acceptance criteria. The remaining issue is projection completeness, not key lookup failure.

## Round 3

### Candidate Generator

1. B3-1: Why do blog knowledge_card artifacts store raw HTML as summaries instead of distilled claims, reusable patterns, and risks?
2. B3-2: Why does GitHub repo understanding rely mostly on README/manifests/tests/entrypoints rather than deeper architecture extraction from code structure?
3. B3-3: Why does repository_understanding not produce explicit transferable patterns tied to target issue decisions and acceptance criteria?
4. B3-4: Why is the target project codebase not scanned into the BuildContextManifest before issue compilation?
5. B3-5: Why can Issue Factory generate target project issues without knowing what files already exist in the target repo and what state tests are in?
6. B3-6: Why does the M0TR-003 handoff cite evidence IDs but not include readable evidence excerpts from those sources?
7. B3-7: Why does source analysis create only one evidence snippet per source, losing the multi-claim evidence needed for issue decomposition?
8. B3-8: Why does the UI show `Relation to goal` from source understanding but not show how each claim became a concrete issue or was rejected?
9. B3-9: Why is source analysis synchronous-looking and instant for repos even though real repo understanding should expose fetch/scan/analyze phases and limitations?

### Four Independent Reviewer Outputs

#### Reviewer 1: AI Builder User

- Keep: B3-1, B3-3, B3-4, B3-5, B3-6, B3-8, B3-9.
- Drop: B3-2 as too implementation-specific for users; B3-7 as standalone.
- Merge / Rewrite: B3-4+B3-5 into missing visible current codebase snapshot; B3-3+B3-8 into missing claim-to-issue decision trail; B3-1+B3-7 into shallow/raw summaries.
- New questions: claims separated from boilerplate; repo scan limits visible; source claim -> target gap -> issue decision -> acceptance criteria; warning when codebase snapshot is null; handoff actionability without raw IDs.
- Evidence: raw HTML knowledge cards; repository_understanding artifacts; no build-context codebase snapshot; generic M0TR-003 reason.

#### Reviewer 2: Knowledge Agent Engineer

- Keep: B3-1, B3-2, B3-3, B3-4, B3-5, B3-6, B3-7, B3-8.
- Drop: B3-9 as standalone.
- Merge / Rewrite: B3-2+B3-3 into shallow repo inventory vs transferable patterns; B3-4+B3-5 into issue compilation without target state; B3-6+B3-7+B3-8 into missing readable multi-claim trace.
- New questions: validator for malformed source artifacts; record source-analysis limitations; typed inspected/skipped files; artifact proving target repo state influenced generation; handoff source excerpts.
- Evidence: raw HTML, shallow repo scan, null codebase snapshot, generic handoff reason, `ClaimWithEvidence` and `SourceInsight` model intent.

#### Reviewer 3: Issue Factory Reviewer

- Keep: B3-1, B3-3, B3-4, B3-5, B3-6, B3-7, B3-8.
- Drop: B3-2 standalone and B3-9.
- Merge / Rewrite: B3-2+B3-3; B3-4+B3-5; B3-6+B3-7+B3-8.
- New questions: exact claims behind each issue; whether issue factory compared existing target files; whether raw HTML refs ground tickets; minimum repo-understanding fields; downgrade when codebase snapshot is null.
- Evidence: `SourceAnalysisService._analyze_text_source()` broad summary; `_analyze_repository_path()` stores inventory, not deep architecture; `assemble_issue_factory_context()` supports codebase snapshot but current manifest lacks one.

#### Reviewer 4: Handoff And Dogfood Reviewer

- Keep: B3-1, B3-3, B3-4, B3-5, B3-6, B3-7, B3-8.
- Drop: B3-9 or lower priority.
- Merge / Rewrite: B3-2+B3-3 into repo patterns mapped to decisions; B3-4+B3-5 into compiling issues with `codebase_snapshot_artifact_id=null`; rewrite B3-6 around readable evidence excerpts.
- New questions: handoff includes target git status/files/tests; existing affected files produce update vs bootstrap tickets; raw HTML quality gate; open one evidence ref to justify issue; scanner limitations surfaced.
- Evidence: handoff has IDs and allowed paths but no readable excerpts; target repo files exist; source artifact quality is uneven.

### Judge Scoring And Merge Decision

- B3-1: 24/25, keep P0.
- B3-2+B3-3: 22/25, merge as shallow repository understanding / missing transferable patterns.
- B3-4+B3-5: 25/25, merge as target codebase state absent from issue generation.
- B3-6+B3-7+B3-8: 23/25, merge as missing readable claim-to-issue-to-handoff trace.
- B3-9: 15/25, fold into source artifact limitations rather than standalone.

### Round Ledger

#### Keep

- Raw HTML source artifacts are not knowledge.
- Repository understanding is too shallow unless it maps patterns to decisions.
- Target codebase snapshot is absent despite existing target repo state.
- Handoffs cite IDs but lack readable evidence excerpts.
- Source claims are too shallow for multi-issue decomposition.

#### Drop

- Repo scanner implementation detail as standalone user-facing issue.
- Synchronous-looking lifecycle as standalone.

#### Merge

- Shallow repo scan + missing transferable patterns.
- Missing codebase snapshot + issue generation without target state.
- Evidence IDs + one-snippet sources + no claim-to-issue trace.

#### Remaining Gaps

- Feedback loop may be deriving next tickets from false execution facts.
- Dirty target repo may contaminate changed_files and memory.

#### Next Focus

Connect source/handoff quality to real dogfood execution evidence and feedback mutation.

## Round 4

### Candidate Generator

1. B4-1: Why does issue detail retrieval by visible issue key return null fields while the board displays that issue as current work?
2. B4-2: Why can handoff evidence remain opaque IDs instead of readable source claims that Codex/Claude and human reviewers can use?
3. B4-3: Why does a blocked execution result list pre-existing untracked files as changed_files even when git_diff is empty and Codex did not run?
4. B4-4: Why does next_tickets.json claim the backend was not blocked and tests passed when execution_log says blocked and test_exit_code is null?
5. B4-5: Why does feedback reflection record one ticket as both blocked and done in ProjectKnowledge OutcomesLog?
6. B4-6: Why is the target repo dirty/untracked state not handled before issue generation, handoff, execution evidence, and review?
7. B4-7: Why does the product not distinguish `blocked before agent execution` from `agent ran and produced code but review blocked`?
8. B4-8: Why can next-ticket generation use misleading changed_files from dirty worktree state instead of per-run diff evidence?
9. B4-9: Why does the dogfood closure path still not prove a target project version advanced if the only visible run is pre-execution blocked?

### Four Independent Reviewer Outputs

#### Reviewer 1: AI Builder User

- Keep: B4-1, B4-2, B4-3, B4-4, B4-6, B4-7, B4-8, B4-9.
- Drop: B4-5 standalone.
- Merge / Rewrite: B4-3+B4-8; B4-4+B4-5; B4-6+B4-7; rewrite B4-1 as board-to-detail contract.
- New questions: target repo preflight; distinguish pre-existing vs AgentRun files; suppress success claims after pre-execution block; repair action for external_execution_blocked; detail lookup failure diagnostics.
- Evidence: blocked execution log, dirty target repo, contradictory next tickets.

#### Reviewer 2: Knowledge Agent Engineer

- Keep: B4-1, B4-2, B4-3, B4-4, B4-6, B4-7, B4-8, B4-9.
- Drop: B4-5 unless confirmed directly.
- Merge / Rewrite: B4-3+B4-8; B4-4+B4-7; B4-2 into evidence-lineage questions; rewrite B4-1 around board/detail fact center.
- New questions: key/id invariant; changed-files computation; next-ticket gate on blocked/test state; reflect classification for external_execution_blocked; preflight artifact; trace issue detail to handoff/execution.
- Evidence: `external_execution_blocked`, empty diff, null tests, dirty changed files, next-ticket contradiction.

#### Reviewer 3: Issue Factory Reviewer

- Keep: B4-1, B4-2, B4-3, B4-4, B4-6, B4-7, B4-8.
- Drop: B4-5 unless confirmed; B4-9 standalone.
- Merge / Rewrite: B4-3+B4-6+B4-8; B4-4+B4-7; B4-1+B4-2 into readable factual chain.
- New questions: detail lookup contract; handoff dereference of evidence; changed-files path; next-ticket inputs; hard-fail next-ticket generation on blocked/null tests.
- Evidence: dirty target repo and contradictory downstream next-ticket output.

#### Reviewer 4: Handoff And Dogfood Reviewer

- Keep: B4-1, B4-2, B4-3, B4-4, B4-6, B4-7, B4-8, B4-9.
- Drop: B4-5 unless directly confirmed.
- Merge / Rewrite: B4-3+B4-6+B4-8; B4-4+B4-7; rewrite B4-1 around complete detail contract.
- New questions: clean baseline git status; next tickets actual inputs; Workbench state for blocked before execution; detail API tests; per-run diff proof.
- Evidence: execution blocked, empty diff, null tests, changed_files from dirty repo, next-ticket false claims.

### Judge Scoring And Merge Decision

- B4-2: 23/25, keep as readable handoff evidence.
- B4-3+B4-6+B4-8: 25/25, merge as dirty worktree contaminates run evidence and feedback.
- B4-4+B4-7: 25/25, merge as feedback loop ignores execution terminal state.
- B4-9: 21/25, keep as dogfood closure gap.
- B4-1: corrected. Keep only as projection/detail completeness, not key lookup failure.
- B4-5: 17/25. Keep only if supported by OutcomesLog evidence; otherwise fold into feedback-state consistency.

### Round Ledger

#### Keep

- Handoffs need readable source claims, not only IDs.
- Dirty target worktree state contaminates blocked-run changed_files.
- Next-ticket generation contradicts execution log.
- Product must distinguish pre-execution blocked from ran-and-review-blocked.
- Dogfood has not proven target version advancement.

#### Drop

- False formulation that issue detail lookup itself is broken; corrected to projection completeness.
- OutcomesLog double-state as standalone unless used with direct evidence.

#### Merge

- Dirty worktree + changed_files + next-ticket contamination.
- Blocked-before-execution + false next-ticket success claims.

#### Remaining Gaps

- Need final invariants that would prevent these regressions.

#### Next Focus

Condense all findings into final product invariants and final grill list.

## Round 5

### Candidate Generator

1. B5-1: What invariant proves a source-generated issue set is current, grounded, and separate from review-feedback/repair deltas?
2. B5-2: What invariant proves every issue visible on the board has a fetchable detail page with body, source links, evidence, handoff, assignments, execution, review, blocker, and next-action fields?
3. B5-3: What invariant proves every issue/repair ticket is executable before assignment: non-empty affected modules, acceptance criteria, allowed paths, test command, and evidence or blocker refs?
4. B5-4: What invariant proves ProjectKnowledge was used, or clearly discloses deterministic fallback, for each generated issue delta?
5. B5-5: What invariant proves source artifacts are real distilled knowledge rather than raw HTML, README inventory, or task-title leakage?
6. B5-6: What invariant proves the target codebase state was scanned and compared before issue generation and before execution evidence is interpreted?
7. B5-7: What invariant proves changed_files, tests, review, memory, next tickets, and OutcomesLog are derived from one actual AgentRun rather than dirty worktree residue or stale previews?
8. B5-8: What invariant proves the Workbench can complete the mini-code-agent dogfood path from browser source input to real Codex/Claude target repo advancement, not just blocked-run visibility?
9. B5-9: What invariant proves user-facing pages never report `done/applied/ready` when the lower evidence surfaces contradict that status?

### Four Independent Reviewer Outputs

#### Reviewer 1: AI Builder User

- Keep: B5-1, B5-2, B5-3, B5-5, B5-6, B5-7, B5-8, B5-9.
- Drop/demote: B5-4 as raw internal concern; rewrite as user-visible grounded-vs-fallback signal.
- Merge / Rewrite: B5-1+B5-9; B5-3+B5-6 if space tight; B5-4 into confidence/limitations disclosure.
- New questions: current version evidence manifest; assignment blocker for missing grounding; separate external sources vs derived artifacts; browser-only acceptance script; fallback disclosure.

#### Reviewer 2: Knowledge Agent Engineer

- Keep: B5-1, B5-2, B5-4, B5-5, B5-6, B5-7, B5-9.
- Drop: B5-3 standalone and B5-8 standalone for this reviewer.
- Merge / Rewrite: B5-1+B5-4; B5-2+B5-3; B5-6+B5-7; sharpen B5-5.
- New questions: field marking preview class; per-delta provenance record; validator for `title=None`; projection test for list/detail; target repo state artifact; invariant preventing false test-passed claim.

#### Reviewer 3: Issue Factory Reviewer

- Keep: B5-1, B5-3, B5-4, B5-5, B5-6, B5-7, B5-9.
- Drop: B5-8 and B5-2 as standalone for this reviewer.
- Merge / Rewrite: B5-1+B5-9; B5-3 as executable-shape invariant; B5-4+B5-5; B5-6+B5-7.
- New questions: source of truth for current issue set; per-issue grounding manifest; block/downgrade null codebase snapshot; verifier for impossible feedback claims; prevent synthetic source display.

#### Reviewer 4: Handoff And Dogfood Reviewer

- Keep: all B5-1..B5-9.
- Drop: none.
- Merge / Rewrite: B5-1+B5-9; optionally B5-2+B5-3; rewrite B5-4, B5-5, B5-7.
- New questions: pre-assignment validator; artifact proving selected Plan Changes delta; check fails on null codebase snapshot; dogfood status taxonomy; projection test for visible issue keys.

### Judge Scoring And Merge Decision

- B5-1+B5-9: 25/25, final invariant.
- B5-2: 22/25, keep as detail/fact-center invariant.
- B5-3: 23/25, keep as executable-before-assignment invariant.
- B5-4: 24/25 after rewrite, keep as ProjectKnowledge-vs-fallback disclosure.
- B5-5: 25/25, keep as source artifact quality invariant.
- B5-6: 25/25, keep as target codebase grounding invariant.
- B5-7: 25/25, keep as per-run evidence integrity invariant.
- B5-8: 24/25, keep as dogfood closure invariant.

### Round Ledger

#### Keep

- Current source-generated issue set must be grounded and selected separately from repair/review previews.
- Every board issue needs a complete detail/fact-center projection.
- Every executable ticket needs non-empty handoff-critical fields.
- ProjectKnowledge use or deterministic fallback must be disclosed.
- Source artifacts need quality gates.
- Target codebase state must be part of compile and run interpretation.
- Per-run evidence must not mix with dirty worktree residue.
- Browser dogfood closure must show real target repo advancement.
- Status labels must be mechanically backed by lower evidence.

#### Drop

- Raw ProjectKnowledge API exposure.
- Detail-key lookup failure formulation, after correction.

#### Merge

- Current issue set invariant + status honesty.
- ProjectKnowledge/fallback disclosure + source artifact quality where useful.
- Target codebase snapshot + per-run evidence integrity where useful.

#### Remaining Gaps

- Convert final grill list into implementation roadmap after review; this workflow stops at grill issues.

#### Next Focus

Write final 20-25 item grill list.
