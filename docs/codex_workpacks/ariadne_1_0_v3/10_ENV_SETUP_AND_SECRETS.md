# 10 — Environment Setup and Secrets

Ariadne 1.0 must work without secrets by using fixtures and FakeCodexBackend.

External credentials are optional and should only enable real adapters.

## Recommended `.env.example`

Create `.env.example`:

```bash
# Optional OpenAI / Codex-related configuration
OPENAI_API_KEY=
ARIADNE_CODEX_COMMAND_TEMPLATE=codex exec --cd {target_repo} --prompt-file {handoff_path}

# Optional Anthropic / Claude Code-related configuration
ANTHROPIC_API_KEY=
ARIADNE_CLAUDE_COMMAND_TEMPLATE=claude --print --dangerously-skip-permissions < {handoff_path}

# Optional GitHub read access for future repo analysis
GITHUB_TOKEN=

# Optional Feishu write-back
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_FOLDER_TOKEN=
FEISHU_BASE_URL=https://open.feishu.cn
FEISHU_ENABLE_WRITE=0

# Ariadne safety flags
ARIADNE_ENABLE_EXTERNAL_EXECUTION=0
ARIADNE_ENABLE_FEISHU_WRITE=0
```

Do not create `.env` with real values.

## What the human owner may provide to Codex runtime

For the current coding session, the human can provide:

1. repository access;
2. local Codex CLI already authenticated, or API key if using API-based adapter;
3. optional Anthropic key if Claude Code adapter is needed;
4. optional Feishu app credentials if real write-back is desired;
5. target repo path if not using demo target repo.

But Ariadne 1.0 must not require these to pass tests or run the default demo.

## Safety defaults

Default configuration must be:

```text
external execution disabled unless confirmed
Feishu writes disabled unless confirmed
fake-codex backend for full demo
all secret files gitignored
```
