# Ariadne Domain Glossary

## Merge Gate

**Definition:** The required evidence check before Codex may merge an Ariadne PR without waiting for the owner.

**Canonical rule:** Codex may auto-merge only when the PR scope matches the current issue, CI is green, local verification is recorded, browser evidence exists when product behavior changed, no fake/demo/mock product path is used as acceptance, and the PR does not include later-issue work.

**Not:** A blanket permission to merge anything that compiles.

**Why it matters:** The Project Version Delivery closure campaign needs continuous execution, but main must remain trustworthy.

## Closure Ledger

**Definition:** The single browser-driven evidence object that proves whether Ariadne advanced the current target project version.

**Canonical rule:** The only final product-closure judge is `scripts/verify_dogfood_browser.sh --real`. It must produce either `REAL_CLOSED` or `BLOCKED_WITH_EVIDENCE`.

**Valid blocked state:** `BLOCKED_WITH_EVIDENCE` is valid only for external blockers: Codex/Claude CLI unavailable, not logged in, quota or rate limit, execution gate disabled, target repo permission, or target repo git state.

**Invalid blocked state:** Stale selectors, missing UI actions, un-analyzed sources, empty handoff, missing evidence回流, mock/fake/demo execution, or CLI-only success are Ariadne defects and must be fixed.

**Why it matters:** Local component evidence repeatedly hid the fact that the promised Project Version Delivery loop was not closed.

## Dogfood Browser Verifier

**Definition:** The browser automation entrypoint that drives the same Project Version Delivery path a user would use in Workbench.

**Canonical rule:** `scripts/verify_dogfood_browser.sh --real` must stay current with the Workbench UI before real backend execution or closure evidence can be accepted.

**Not:** A replacement product path, a direct API smoke test, or a CLI-only harness.

**Why it matters:** A stale verifier selector is an Ariadne defect, not an external blocker.

## Real Backend Closure

**Definition:** The required product closure state where Ariadne uses a real Codex or Claude backend to modify the target project repository.

**Canonical rule:** For the current closure campaign, a real backend attempt is not enough. Codex or Claude must successfully change target project code, and Ariadne must capture the resulting diff, changed files, test result, review result, and Workbench evidence.

**Not:** A blocked external execution attempt, a fake-codex run, a dry-run, or an execution that only writes Ariadne artifacts without changing the target repository.

**Why it matters:** Ariadne is being judged as an AI Builder workbench that advances a target project version, not merely as an orchestrator that can call a backend.

## Dogfood Target Repository

**Definition:** The local repository Ariadne must advance during the Project Version Delivery closure campaign.

**Canonical rule:** Use `/Users/martinlos/code/ariadne-dogfood/mini-code-agent` as the controlled dogfood target repo for real Codex/Claude closure.

**Required properties:** It must be a local git repository with a minimal test command, a clear v0.1 project goal, and a bounded code change that Codex/Claude can implement from Ariadne's handoff.

**Not:** The Ariadne repository itself, a remote open-source repository modified in place, or a fixture-only demo directory.

**Why it matters:** Real Backend Closure requires a target repo that can be safely changed and verified without polluting Ariadne's own source tree.

## External Execution Blocker

**Definition:** A non-Ariadne condition that prevents real Codex or Claude from successfully modifying the dogfood target repository.

**Canonical rule:** During the current closure campaign, external execution blockers stop the goal and require owner intervention. They are not acceptable completion states.

**Examples:** Codex CLI unavailable, Claude CLI unavailable, not logged in, quota exhausted, invalid `service_tier`, target repo permission problems, or target repo git state that prevents a safe edit.

**Not:** Missing Ariadne implementation, stale Workbench selector, missing handoff content, empty evidence, fake-codex fallback, dry-run success, or CLI-only success.

**Why it matters:** The closure campaign requires real backend code modification; an external blocker can explain why work stopped, but cannot count as completion.
