# Provider Capability Schema Template

```json
{
  "backend_name": "codex",
  "available": true,
  "command_path": "/opt/homebrew/bin/codex",
  "supports_prompt_file": false,
  "supports_stdin": true,
  "supports_session_resume": false,
  "supports_mcp": false,
  "skill_materialization_strategy": "handoff_inline",
  "supports_model_selection": true,
  "supports_reasoning_effort": true,
  "supports_timeout": true,
  "supports_diff_capture": true,
  "supports_test_capture": true,
  "requires_confirmation": true,
  "requires_external_execution_gate": true,
  "recommended_command_template": "codex exec -c model_reasoning_effort=\"none\" --cd {target_repo} - < {handoff_file}",
  "known_limitations": []
}
```

