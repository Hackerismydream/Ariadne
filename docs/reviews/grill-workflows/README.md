# Ariadne Grill Workflows

This folder contains promptable workflows for running separate grill threads.

All workflows require the `grill-me` skill:

```text
/Users/martinlos/.codex/skills/grill-me/SKILL.md
```

They use `grill-me` as the strict questioning standard, but run it as an
unattended multi-round review instead of stopping after each question for user
input. Where reviewer or judge subagents are required, use real subagents if
available; otherwise simulate isolated subagents and label them.

Use them in this order:

1. `2026-06-24-multica-parity-grill-workflow.md`
   - Reviews the lower Multica-style work-management layer.
2. `2026-06-24-knowledge-orchestration-grill-workflow.md`
   - Reviews the upper Ariadne knowledge/source/feedback-to-ticket layer.
3. `2026-06-24-final-judge-merge-workflow.md`
   - Merges both outputs into a final 41-item grill list.

The split is intentional:

```text
Thread A: Is Ariadne a convincing Multica-grade issue / agent / runtime workbench?
Thread B: Does Ariadne turn external knowledge and feedback into executable target-project tickets?
Thread C: Which 41 questions matter most after deduplication and scoring?
```

Do not use these workflows as implementation plans. They are review workflows.
Implementation planning starts only after the final 41 grill list exists.
