# Runtime Capability Schema

```json
{
  "id": "",
  "provider": "fake-codex|shell|codex|claude-code|deepseek|feishu",
  "command": "",
  "version": "",
  "available": true,
  "status": "available|missing|blocked|unknown",
  "doctor_notes": [],
  "checked_at": "",
  "env_gates": {
    "ARIADNE_ENABLE_EXTERNAL_EXECUTION": "set|unset",
    "ARIADNE_CODEX_COMMAND_TEMPLATE": "set|unset",
    "ARIADNE_CLAUDE_COMMAND_TEMPLATE": "set|unset",
    "FEISHU_ENABLE_WRITE": "set|unset",
    "DEEPSEEK_API_KEY": "set|unset"
  }
}
```
