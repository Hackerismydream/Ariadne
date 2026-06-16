# Skill Materialization Schema Template

```json
{
  "skill_name": "codex-handoff",
  "backend_name": "codex",
  "materialization_strategy": "handoff_inline",
  "source_skill_path": ".skills/codex-handoff/SKILL.md",
  "materialized_artifact_path": ".ariadne/artifacts/<ticket>/codex_handoff.md",
  "requires_confirmation": false,
  "notes": "Inline the skill into the handoff prompt. Do not write to external Codex config by default."
}
```

