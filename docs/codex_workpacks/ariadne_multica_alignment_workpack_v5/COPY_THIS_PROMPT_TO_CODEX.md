# Master Prompt — ARI-005 Multica Architecture Alignment

You are Codex working on Ariadne.

Ariadne already has a working True MVP loop and a real CodexBackend smoke-test path. Now we need to prevent architecture drift by studying Multica deeply and aligning Ariadne with Multica's agent work-management architecture.

## Repository to study

```text
https://github.com/multica-ai/multica
```

## Read this workpack first

Read all files in:

```text
docs/codex_workpacks/ariadne_multica_alignment_workpack_v5/
```

If the path differs after extraction, locate the workpack by filename.

Required reading inside this workpack:

```text
00_START_HERE.md
01_CURRENT_ARIADNE_STATE.md
02_MULTICA_READING_PLAN.md
03_MULTICA_ARCHITECTURE_DIGEST_SPEC.md
04_GAP_REPORT_SPEC.md
05_ADR_0002_SPEC.md
06_IMPLEMENTATION_SCOPE.md
07_TEST_AND_ACCEPTANCE.md
08_SECURITY_AND_LICENSE.md
templates/MULTICA_OBJECT_MAPPING_TABLE.md
templates/ARIADNE_GAP_ITEM.md
templates/ROUTE_DECISION_SCHEMA.md
templates/RUNTIME_CAPABILITY_SCHEMA.md
templates/PROJECT_RESOURCE_SCHEMA.md
templates/BUILD_SKILL_TEMPLATE.md
```

## Mission

Perform ARI-005: Multica Architecture Alignment.

This task has two parts:

```text
1. Study Multica deeply and produce architecture analysis docs.
2. Implement selected Ariadne architecture-hardening changes inspired by that analysis.
```

Do not copy Multica code.

Do not turn Ariadne into Multica.

## Required architecture outputs

Create:

```text
docs/architecture/multica_architecture_digest.md
docs/architecture/ariadne_multica_gap_report.md
docs/adr/ADR-0002-multica-architecture-alignment.md
docs/smoke_test_results/ARI-004-real-codex-summary.md
```

These are required.

## Required implementation changes

Implement the following unless they already exist:

```text
1. stronger AgentRun lifecycle / compatible lifecycle_state
2. typed failure reasons
3. RuntimeCapability model and backend doctor snapshot persistence
4. ProjectResource model and .ariadne/project/resources.json
5. target repo path validation
6. local directory lock
7. default BuildSkill packs under .skills/
8. handoff skill references
9. route_decision.json artifact
10. progress events for ticket run
11. board display for runtime capability, route decision, project resources, skills, progress events
```

Keep scope local-first and Pythonic.

## Preserve existing behavior

The following must still work:

```bash
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
```

If available:

```bash
uv run ari demo full
uv run ari ticket list
uv run ari ticket run ARI-003 --backend fake-codex
uv run ari export board
uv run ari backend doctor
```

The real Codex smoke-test path must remain gated. Do not require Codex for tests.

## Implementation priorities

If time is limited, prioritize:

```text
architecture docs
failure reasons
runtime capability snapshot
project resources
local directory safety
directory lock
route decision artifact
progress events
tests
```

Do not spend time building UI polish, server architecture, or Feishu real write.

## Tests

Add tests for:

```text
architecture docs exist
ADR-0002 exists
gap report exists
failure reasons
AgentRun lifecycle terminal invariants
runtime capability snapshot
project resources serialization
target path validation
directory lock behavior
BuildSkill discovery
handoff skill references
route decision artifact
progress events
existing ticket run full loop
backend doctor secrets safety
```

Tests must not require external services.

## Required commands

Run:

```bash
pytest
ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
```

If `uv run ari` is available, run:

```bash
uv run ari demo full
uv run ari ticket list
uv run ari ticket run ARI-003 --backend fake-codex
uv run ari export board
uv run ari backend doctor
```

## Definition of done

This task is done only if:

```text
Multica architecture digest exists and references actual files inspected.
Ariadne gap report exists and contains implement/defer/avoid decisions.
ADR-0002 exists.
Ariadne code has new lifecycle/failure/resource/runtime/skill/routing/progress foundations.
True MVP loop still passes.
Backend doctor still works and does not print secrets.
Real Codex smoke path remains safety-gated.
Tests pass.
Development report summarizes what was learned from Multica and what changed in Ariadne.
```

## Final response

At the end, report:

```text
1. Multica files/docs inspected.
2. Architecture docs created.
3. Key architecture takeaways.
4. Ariadne gaps found.
5. Code changes implemented.
6. Commands run.
7. Test results.
8. Whether True MVP loop still passes.
9. Whether real Codex smoke path remains gated.
10. Known limitations.
11. Next recommended Build Ticket.
```
