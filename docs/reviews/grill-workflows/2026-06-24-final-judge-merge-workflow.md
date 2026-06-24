# Ariadne Grill Workflow C: Final Judge Merge

## Purpose

Use this workflow after Workflow A and Workflow B have produced their final
grill lists.

This thread must answer one question:

```text
What are the final 41 high-quality, executable, evidence-backed grill issues
that should drive Ariadne from its current state toward a Multica-grade AI
Builder Agent Workbench?
```

## Inputs

Required input files:

```text
/Users/martinlos/code/Ariadne/docs/reviews/grill-workflows/results/YYYY-MM-DD-multica-parity-final-grill-list.md
/Users/martinlos/code/Ariadne/docs/reviews/grill-workflows/results/YYYY-MM-DD-knowledge-orchestration-final-grill-list.md
```

Also read:

```text
/Users/martinlos/code/Ariadne/AGENTS.md
/Users/martinlos/code/Ariadne/README.md
/Users/martinlos/code/Ariadne/docs/adr/ADR-0004-ticket-centered-agent-workbench.md
/Users/martinlos/code/Ariadne/docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md
```

## Hard Rules

- Do not invent issues that are not supported by either grill list unless there
  is a concrete evidence gap found while merging.
- Do not preserve duplicates just because they came from different threads.
- Do not keep vague issues like "improve UX" or "make agents smarter".
- Do not turn the final list into implementation tasks yet. It is a grill list:
  question, why it matters, how to verify.
- Do not accept mock, fixture, demo, or CLI-only evidence as product closure.

## Merge Method

### Step 1: Normalize

Convert all MP and KO issues into one table:

```text
id
original source
question
priority
product surface
evidence
verification method
```

### Step 2: Deduplicate

Merge issues when they share the same root failure, even if they appear on
different surfaces.

Keep the sharper wording. Preserve both evidence sources.

### Step 3: Score

Score each issue:

```text
severity: 0-5
dogfood blocker: 0-5
Multica parity relevance: 0-5
knowledge-layer relevance: 0-5
verifiability: 0-5
implementation leverage: 0-5
```

### Step 4: Select 41

The final list must contain exactly 41 issues:

- 12 to 16 lower-layer Multica parity issues
- 12 to 16 upper-layer knowledge orchestration issues
- 8 to 12 cross-layer closure issues

If there are more than 41, cut the lowest-score issues.

If there are fewer than 41, run one additional mini-round:

```text
Find missing grill questions only from evidence already collected.
Do not brainstorm abstract issues.
```

### Step 5: Assign Priority

Use:

```text
P0: blocks real browser dogfood closure
P1: blocks Multica-grade maturity but not the first closure path
P2: important quality or polish issue after closure
```

## Final Output

Write final output to:

```text
/Users/martinlos/code/Ariadne/docs/reviews/grill-workflows/results/YYYY-MM-DD-final-41-grill-list.md
```

Use this structure:

```markdown
# Ariadne Final 41 Grill List

## Executive Summary

## P0: Closure Blockers

## P1: Multica-Grade Maturity Gaps

## P2: Quality And Product Sharpness Gaps

## Cross-Layer Failure Map

## Evidence Appendix

## Rejected / Merged Candidates
```

Each grill issue must use this format:

```markdown
## G-001: <question>

- Priority: P0 | P1 | P2
- Source: MP-xxx | KO-xxx | merged
- Product layer: Multica parity | Knowledge orchestration | Cross-layer
- Evidence:
- Why this matters:
- Verification method:
- First fix direction:
```

## Prompt To Paste Into New Thread

```text
You are the final judge for the Ariadne grill process.

First wait until these two files exist:
/Users/martinlos/code/Ariadne/docs/reviews/grill-workflows/results/YYYY-MM-DD-multica-parity-final-grill-list.md
/Users/martinlos/code/Ariadne/docs/reviews/grill-workflows/results/YYYY-MM-DD-knowledge-orchestration-final-grill-list.md

Then read and follow:
/Users/martinlos/code/Ariadne/docs/reviews/grill-workflows/2026-06-24-final-judge-merge-workflow.md

Your output must be exactly one final markdown file with 41 evidence-backed
grill issues. Do not implement fixes. Do not create a roadmap yet.
```
