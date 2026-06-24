# Ariadne Knowledge Orchestration Final Grill List

Date: 2026-06-24

Workflow:
`docs/reviews/grill-workflows/2026-06-24-knowledge-orchestration-grill-workflow.md`

Process evidence:
`docs/reviews/grill-workflows/results/2026-06-24-knowledge-orchestration-grill-process-notes.md`

Browser evidence:

- `docs/reviews/grill-workflows/results/2026-06-24-knowledge-sources.png`
- `docs/reviews/grill-workflows/results/2026-06-24-knowledge-plan-changes.png`
- `docs/reviews/grill-workflows/results/2026-06-24-knowledge-issues.png`

## Five-Round Execution Self-Check

- Round 1 completed: yes
- Round 2 completed: yes
- Round 3 completed: yes
- Round 4 completed: yes
- Round 5 completed: yes
- Each round had exactly 9 candidates: yes
- Each round had 4 independent reviewer subagent outputs: yes
- Each round had judge scoring / merge decision / ledger: yes

## KO-001: What invariant proves the current source-generated issue set is selected, grounded, and separate from review-feedback or repair deltas?

- Priority: P0
- Product promise: The user should see the current version issue set generated from sources and goal, not whichever preview happened most recently.
- Ariadne evidence: Browser `#plan-changes` defaults to `backlog_preview_d28c447255c1`, a `review_feedback` preview with `未命名任务` and ungrounded repair items, while the original source-generated `manual_goal` preview is `backlog_preview_8aa11cc0eca5`.
- Source / artifact evidence: Original `manual_goal` preview has 10 operations with source artifacts, evidence refs, affected modules, and acceptance criteria.
- Why this must be fixed: If Plan Changes can silently switch from source delta to repair delta, the user cannot trust what "current plan" means.
- Verification method: `#plan-changes` must identify preview type, trigger, target project/version, and whether it is current mainline, repair, feedback, or historical.
- Suggested owner area: `ariadne_ltb/application/current_version_scope.py`, `ariadne_ltb/application/project_version_delivery.py`, Plan Changes projection.

## KO-002: Why does the Workbench report `done` / `applied` / `ready` when lower evidence surfaces contradict that status?

- Priority: P0
- Product promise: Current Version Context should be an honest delivery state machine.
- Ariadne evidence: Current Version Context says sources readiness and issue delta are done/applied while browser `#sources` shows 61 sources but only 9 ready, and `#issues` shows most planning cards as `0 evidence`.
- Source / artifact evidence: `/api/workbench` reports `sources=61`, `sourceArtifacts=9`, `sourceEvidence=9`.
- Why this must be fixed: Status optimism makes Ariadne feel like a demo dashboard rather than an operational workbench.
- Verification method: Context strip must compute readiness from the same evidence that powers Sources, Plan Changes, and Issues.
- Suggested owner area: `ariadne_ltb/application/workbench_projection.py`, CurrentVersionContext frontend.

## KO-003: Why does `/api/issues` hide source grounding that exists in persisted BuildTicket metadata?

- Priority: P0
- Product promise: Issue cards should show whether work is grounded in source evidence.
- Ariadne evidence: Persisted `M0TR-001..010` tickets each have 9 `evidence_refs`, 9 `source_artifact_ids`, 9 `source_document_ids`, affected modules, and 3 acceptance criteria; browser/API issue list still shows 9 backlog issues as `0 evidence`.
- Source / artifact evidence: `WorkbenchIssuesService._issue_item()` computes list `evidence_count` from execution count, review count, and `ticket.artifact_ids`, not source evidence metadata.
- Why this must be fixed: The system may have grounding, but the Workbench makes it look ungrounded.
- Verification method: For every issue, list/detail evidence counts must include source evidence, source artifacts, build context, handoff, execution, review, and artifacts by category.
- Suggested owner area: `ariadne_ltb/application/workbench_issues.py`.

## KO-004: Why does issue detail projection omit handoff-critical metadata such as acceptance criteria and affected modules?

- Priority: P0
- Product promise: Issue detail is the fact center before assignment and execution.
- Ariadne evidence: `GET /api/issues/M0TR-001 | jq .issue` returns `acceptance_criteria=null` and `affected_modules=null`, while the persisted ticket metadata contains both.
- Source / artifact evidence: `issue_factory.py` stores `acceptance_criteria` and `affected_modules` in operation/ticket metadata.
- Why this must be fixed: Users and agents cannot evaluate executability if the detail page hides the fields that drive handoff quality.
- Verification method: Every visible issue detail should expose title, body, source links, evidence refs, source artifacts, affected modules, acceptance criteria, handoff status, assignments, runs, review, blockers, and next actions.
- Suggested owner area: `ariadne_ltb/application/workbench_issues.py`, issue detail frontend.

## KO-005: What blocks an issue or repair ticket from assignment when title, evidence, affected modules, acceptance criteria, allowed paths, or test command are missing?

- Priority: P0
- Product promise: Ariadne should not hand Codex/Claude vague work.
- Ariadne evidence: `review_feedback` preview renders `M0TR-003` as `未命名任务` with 0 artifacts, 0 evidence refs, 0 acceptance criteria, and 0 affected modules; repair tickets `ARI-074..076` also lack grounding metadata.
- Source / artifact evidence: `create_handoff_packet()` depends on affected modules, acceptance criteria, test command, and evidence refs to build useful handoff content.
- Why this must be fixed: Empty repair work can become another low-quality agent task and loop the system.
- Verification method: Assignment should be blocked or downgraded unless executable fields are present, or the ticket is explicitly a human/blocker triage item.
- Suggested owner area: assignment validation, handoff packet generation, Plan Changes validation.

## KO-006: What proves ProjectKnowledge was used for an issue delta, and where is deterministic fallback disclosed?

- Priority: P0
- Product promise: Phase 8 should not imply knowledge orchestration when the old deterministic compiler produced the result.
- Ariadne evidence: `.ariadne/knowledge/resource_56a27abf28d0/` contains only `outcomes_log.json` and one blocker learning; no `source_insights` or `synthesis_themes` were present for the current build context.
- Source / artifact evidence: `ariadne_ltb/knowledge/__init__.py` falls back to deterministic compilation when no DeepSeek key, graph failure, empty specs, or empty theme fallback occurs.
- Why this must be fixed: Without provenance, users cannot tell whether issues came from ProjectKnowledge or old templates.
- Verification method: Every backlog preview should record compiler path: ProjectKnowledge graph, deterministic theme fallback, old issue compiler, error/fallback reason, and generated artifact paths.
- Suggested owner area: `ariadne_ltb/knowledge/__init__.py`, backlog preview metadata, Plan Changes UI.

## KO-007: Why are source artifacts allowed to persist raw HTML as "knowledge"?

- Priority: P0
- Product promise: A pasted blog should become distilled claims, patterns, risks, and decisions.
- Ariadne evidence: Multiple `knowledge_card` payload summaries begin with raw `<!doctype html>...`.
- Source / artifact evidence: `SourceAnalysisService._analyze_text_source()` collapses fetched content and truncates it into a summary, so page boilerplate can become a knowledge card.
- Why this must be fixed: Raw HTML cannot ground issue generation or handoff instructions.
- Verification method: Source artifact validation must reject or mark malformed artifacts, and the UI must show extraction quality/limitations.
- Suggested owner area: `ariadne_ltb/application/source_analysis.py`, source artifact quality gate.

## KO-008: Why is GitHub repository understanding mostly inventory instead of transferable architecture understanding?

- Priority: P0
- Product promise: A GitHub repo input should help reduce build friction by extracting reusable patterns, risks, architecture, and test strategy.
- Ariadne evidence: `repository_understanding` artifacts contain README summaries, identity, manifests, entrypoints, tests, selected files, and scan warnings.
- Source / artifact evidence: `repository_scanner.py` selects README, manifests, entrypoints, tests, and first files; it does not extract call graph, module responsibilities, agent loop architecture, tool protocol, or safety model.
- Why this must be fixed: Inventory alone does not explain why specific issues exist or how to implement them.
- Verification method: Repo artifact must include inspected files, extracted patterns, avoid notes, architecture map, confidence/limits, and issue-decision links.
- Suggested owner area: repository scanner, source analysis, ProjectKnowledge ingest nodes.

## KO-009: Why can target-project issues be generated while `codebase_snapshot_artifact_id` is null?

- Priority: P0
- Product promise: Ariadne should generate work for the current local project, not an abstract target.
- Ariadne evidence: `build_context_825e3a5124d7` has source/artifact/evidence ids but `codebase_snapshot_artifact_id=null`.
- Source / artifact evidence: The target repo `/Users/martinlos/code/ariadne-dogfood/mini-code-agent` already contains `mini_code_agent/`, `pyproject.toml`, `tests/`, and untracked state.
- Why this must be fixed: Issue Factory may duplicate already-created work or miss the real next slice.
- Verification method: Issue generation should require, warn on, or explicitly downgrade confidence when target codebase snapshot is missing.
- Suggested owner area: `ariadne_ltb/application/build_context.py`, target project registry, source analysis.

## KO-010: Why is there no visible source claim -> issue decision -> acceptance criteria trace?

- Priority: P0
- Product promise: Users should understand why a source produced a specific issue.
- Ariadne evidence: Plan Changes shows artifact/evidence ids or empty states; Issues show evidence counts/source links, but not the claim-to-decision path.
- Source / artifact evidence: M0TR handoff cites 9 evidence IDs, but its task reason is generic: "Reference code-agent projects converge on typed action and observation contracts."
- Why this must be fixed: The product remains a manual notes board unless users can audit how knowledge became work.
- Verification method: For each issue, display source claim, locator, confidence, ProjectKnowledge theme or fallback disclosure, affected module rationale, and acceptance criteria rationale.
- Suggested owner area: Plan Changes projection, issue detail projection, handoff rendering.

## KO-011: Why do handoffs cite evidence IDs without readable excerpts, locators, and source claims?

- Priority: P0
- Product promise: Codex/Claude handoffs should be self-contained enough to execute.
- Ariadne evidence: `M0TR-003` handoff includes evidence refs and allowed paths but not readable source excerpts.
- Source / artifact evidence: Source evidence records exist, but the handoff only lists IDs.
- Why this must be fixed: Coding agents should not reverse-engineer `.ariadne` state to understand why a task exists.
- Verification method: Handoff markdown should include concise evidence excerpts, source titles, locators, and claim summaries for every referenced source.
- Suggested owner area: handoff packet generation.

## KO-012: Why are synthetic task-derived sources visible beside real external inputs?

- Priority: P1
- Product promise: Sources should mean user-provided or externally fetched inputs.
- Ariadne evidence: Sources page includes task-title-like rows such as `Capture git diff and test result`, `Implement shell command tool with allowlist`, and review-feedback sources.
- Source / artifact evidence: `issue_factory.py` can synthesize `SourceDocument` values from task titles via `_source_for_task`.
- Why this must be fixed: Output leaking back into input destroys source lineage and user trust.
- Verification method: UI must distinguish raw user sources, derived source artifacts, review feedback, execution feedback, and synthetic internal sources.
- Suggested owner area: source model metadata, Sources page filters, issue factory source synthesis.

## KO-013: Why can a source lane show 61 sources but provide no operational queue explaining what blocks the other 52?

- Priority: P1
- Product promise: Adding sources should start an understandable lifecycle.
- Ariadne evidence: Browser `#sources` shows 61 sources, 9 ready, many queued, with broad messages like "已保存，等待分析或抓取。"
- Source / artifact evidence: API has `projectInputs=61`, `sourceArtifacts=9`, `sourceEvidence=9`.
- Why this must be fixed: The user cannot know whether to wait, re-analyze, delete, prioritize, or ignore pending sources.
- Verification method: Sources page should group queued/analyzing/blocked/analyzed/ignored/stale and show the next action per source.
- Suggested owner area: source lifecycle service and Sources UI.

## KO-014: Why does source analysis usually create only one broad evidence snippet per source?

- Priority: P1
- Product promise: One repo/blog should support multiple independent build decisions.
- Ariadne evidence: Current build context uses 9 evidence ids across 9 source artifacts for 10 issues.
- Source / artifact evidence: `SourceAnalysisService` saves one broad evidence claim for text/repo analysis paths.
- Why this must be fixed: Multi-issue decomposition needs multiple claims: loop protocol, tool safety, trace format, tests, reviewer strategy, UX.
- Verification method: Each non-trivial source should produce multiple typed claims with locator/confidence, and issue generation should cite the exact claims used.
- Suggested owner area: source analysis, ProjectKnowledge ingest, evidence model.

## KO-015: Why is source-analysis limitation not surfaced to the Issue Factory or user?

- Priority: P1
- Product promise: Shallow understanding should not be sold as deep understanding.
- Ariadne evidence: Repo understanding is README/manifests/tests-focused; UI labels it as analyzed/ready.
- Source / artifact evidence: Scanner warnings exist, but the Workbench does not make scan depth/limitations prominent in Plan Changes or handoff risk.
- Why this must be fixed: Low-depth evidence should lower confidence or require more analysis before generating high-priority issues.
- Verification method: Artifacts should include scan depth, skipped files, limits, and confidence; issue delta should show confidence and limitation warnings.
- Suggested owner area: repository scanner, source understanding projection, Plan Changes UI.

## KO-016: Why does next-ticket generation reason from dirty worktree residue instead of per-run diff evidence?

- Priority: P0
- Product promise: Feedback should update the issue set based on what the agent actually did.
- Ariadne evidence: `M0TR-003` execution was blocked before external execution, `git_diff` was empty, `test_exit_code=null`, but `changed_files` listed many pre-existing untracked files.
- Source / artifact evidence: Target repo has untracked `mini_code_agent/`, `pyproject.toml`, `tests/`, `.mini-code-agent/`.
- Why this must be fixed: Feedback-based issue mutation becomes false if it treats prior dirty state as current run output.
- Verification method: ExecutionResult must separate preflight dirty state, per-run changed files, diff, and blocked-before-execution state.
- Suggested owner area: execution backend, result capture, reviewer, next-ticket generator.

## KO-017: Why does `next_tickets.json` contradict the execution log after a blocked run?

- Priority: P0
- Product promise: The feedback loop must be evidence-faithful.
- Ariadne evidence: `next_tickets.json` says "Execution backend was not blocked; Target project tests passed; Changed files are within allowed scope" while `execution_log.json` says `blocked=true`, `failure_reason=external_execution_blocked`, `exit_code=2`, `test_exit_code=null`.
- Source / artifact evidence: M0TR-003 artifacts under `.ariadne/artifacts/ticket_7ce56b0eebb6/`.
- Why this must be fixed: Ariadne cannot safely generate repair or next issues from false premises.
- Verification method: Next-ticket generation must assert consistency with ExecutionResult and ReviewReport before writing suggestions.
- Suggested owner area: next-ticket generator, review, memory/reflect path.

## KO-018: Why does feedback reflection not clearly distinguish pre-execution blockers from executed-but-review-blocked runs?

- Priority: P0
- Product promise: Different failures should produce different repair work.
- Ariadne evidence: Current visible state shows `external_execution_blocked`, but downstream next-ticket text suggests successful backend/tests.
- Source / artifact evidence: `.ariadne/knowledge/.../outcomes_log.json` records blocked learning; next-ticket output does not respect the same state.
- Why this must be fixed: A gate/config blocker should not produce code-quality repair tickets based on nonexistent execution.
- Verification method: Outcome and next-ticket generation should classify `blocked_before_execution`, `executed_failed`, `review_blocked`, and `done` separately.
- Suggested owner area: ProjectKnowledge reflect, next-ticket generator, delivery projection.

## KO-019: Why can dogfood evidence stop at product-visible blocked instead of proving target project version advancement?

- Priority: P0
- Product promise: Ariadne should organize agent team work until a target project reaches a version.
- Ariadne evidence: Current browser evidence shows blocked `M0TR-003`, not browser source input -> real Codex/Claude -> target repo diff/tests/review/memory/next issue closure.
- Source / artifact evidence: Dogfood doc requires `.ariadne/dogfood/<run-id>/closure-result.json` with `status: REAL_CLOSED` for success.
- Why this must be fixed: Blocker visibility is useful, but it is not the promised AI Builder closed loop.
- Verification method: Browser-only dogfood must create/update source, generate delta, apply, assign, run real backend, produce target diff/tests/review/memory/next issue, and update version progress.
- Suggested owner area: dogfood verifier, Workbench orchestration, runtime evidence.

## KO-020: Why is fallback/template issue generation not obvious to the user?

- Priority: P1
- Product promise: Users should know when Ariadne reasoned from sources versus used deterministic fallback.
- Ariadne evidence: Current issue titles match fixed mini-code-agent tasks from the deterministic compiler shape, while `.ariadne/knowledge` lacks source insight/theme files.
- Source / artifact evidence: `issue_compiler.py` contains fixed mini-code-agent task generation; `knowledge/__init__.py` falls back to it.
- Why this must be fixed: Fallback can be useful, but presenting it as knowledge orchestration overstates agent capability.
- Verification method: Issue delta should show compiler mode, fallback reason, model/graph status, and limitations.
- Suggested owner area: knowledge compile integration, Plan Changes UI.

## KO-021: Why does the current issue prefix/key not clearly represent the target project identity?

- Priority: P2
- Product promise: Issue keys should make target project/version context obvious.
- Ariadne evidence: Current issue set uses `M0TR-*` while the dogfood case expected `MCA-*`; the current target label is `M0TR-003 target repository`.
- Source / artifact evidence: `issue_factory.py` derives prefix from project resource label/ref and special-cases mini-code context.
- Why this must be fixed: Ambiguous prefixes make it harder to tell whether issues are Ariadne internal, dogfood target, repair work, or generated from feedback.
- Verification method: Target project registration should explicitly set and display issue prefix; generated issues should preserve it consistently.
- Suggested owner area: target project registry, issue factory prefix derivation.

## KO-022: Why is Plan Changes still a preview browser rather than a reviewed issue-delta decision surface?

- Priority: P1
- Product promise: The user should be able to accept or reject specific source-driven changes with confidence.
- Ariadne evidence: Plan Changes can show `Added`, `Updated`, `Deferred`, `Rejected`, but the selected delta can be a repair-feedback preview with empty fields, and the trace points to `.ariadne/backlog/previews/...` rather than a clear decision rationale.
- Source / artifact evidence: Preview history includes `manual_goal`, `execution_result`, `codebase_observation`, `memory_gap`, and `review_feedback` previews.
- Why this must be fixed: A timeline of previews is not the same as a decision surface for the current project version.
- Verification method: Plan Changes should group current mainline source delta, pending changes, repair suggestions, rejected/deferred work, and history separately.
- Suggested owner area: backlog preview projection, Plan Changes page.

## Top 5 Structural Failures

1. **Current issue set truth is not protected.** Latest preview, review feedback, repair tickets, and mainline source-generated issues can appear on the same surface without a strong semantic boundary.
2. **Evidence exists but is projected inconsistently.** BuildTicket metadata contains source grounding, while issue cards and detail projections omit or undercount it.
3. **Source understanding is too shallow.** Blog artifacts can contain raw HTML; repo artifacts are mostly inventory; ProjectKnowledge source insight/theme artifacts are absent for the current build context.
4. **Target codebase state is not first-class in issue generation.** `codebase_snapshot_artifact_id=null` while target repo state materially affects what should be generated and executed.
5. **Feedback mutation is not evidence-faithful.** Blocked runs, dirty worktree files, empty diffs, null tests, and next-ticket claims can contradict each other.

## Where The Knowledge Layer Is Too Shallow

- It can fetch a page but persist raw HTML instead of distilled claims.
- It can clone/scan a repo but mostly records README/manifests/tests/entrypoints.
- It does not prove SourceInsight/SynthesisTheme persistence for the active issue set.
- It does not expose a claim-to-issue-to-handoff trace.
- It does not clearly disclose fallback/template generation.

## Where The Product Still Feels Like Manual Notes

- Sources are a mixed lane of external inputs, review feedback, and derived task-title documents.
- Plan Changes can show previews and IDs without a clear current-version decision story.
- Issues can look ungrounded even when metadata exists.
- Handoffs cite IDs rather than readable source claims.
- The browser dogfood path currently proves blocked visibility, not real project advancement.

## Evidence Appendix

- Browser `#sources`: 61 sources, 9 ready; screenshot `2026-06-24-knowledge-sources.png`.
- Browser `#plan-changes`: `未命名任务`, 0 artifacts, 0 evidence refs, 0 acceptance criteria, 0 affected modules; screenshot `2026-06-24-knowledge-plan-changes.png`.
- Browser `#issues`: 10 issues, most planning cards show 0 evidence; screenshot `2026-06-24-knowledge-issues.png`.
- `/api/workbench`: `sources=61`, `sourceArtifacts=9`, `sourceEvidence=9`, `projectInputs=61`, `tickets=10`.
- Persisted `M0TR-001..010` BuildTickets: metadata has 9 evidence refs, 9 source artifact ids, 9 source document ids, affected modules, and 3 acceptance criteria.
- `backlog_preview_8aa11cc0eca5`: original `manual_goal` source-generated issue delta with grounded M0TR operations.
- `backlog_preview_d28c447255c1`: latest `review_feedback` preview displayed in Plan Changes with ungrounded repair operations.
- `build_context_825e3a5124d7`: source/artifact/evidence ids present, `codebase_snapshot_artifact_id=null`.
- `.ariadne/knowledge/resource_56a27abf28d0/`: only outcomes/blocker files found, no source insight/theme files.
- M0TR-003 handoff: allowed paths and evidence IDs present, no readable evidence excerpts.
- M0TR-003 execution log: `blocked=true`, `failure_reason=external_execution_blocked`, empty diff, null test result.
- M0TR-003 next tickets: contradict execution log by claiming backend not blocked and tests passed.
