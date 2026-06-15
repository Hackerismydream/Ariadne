# Security, Environment, and Secrets

## No secrets in repo

Never commit:

```text
.env
.env.*
*.secret
secrets/
```

Verify `.gitignore` includes these patterns.

## External execution gating

Real external execution must require both:

```text
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1
--confirm-execution
```

If either is missing, backend must return a blocked result.

## Codex optional environment

```bash
export ARIADNE_ENABLE_EXTERNAL_EXECUTION=1
export ARIADNE_CODEX_COMMAND_TEMPLATE='codex exec --cd {target_repo} --prompt-file {handoff_file}'
```

Do not require this for tests.

## Claude optional environment

```bash
export ARIADNE_ENABLE_EXTERNAL_EXECUTION=1
export ARIADNE_CLAUDE_COMMAND_TEMPLATE='claude --print < {handoff_file}'
```

Do not require this for tests.

## DeepSeek optional environment

```bash
export DEEPSEEK_API_KEY='...'
export DEEPSEEK_BASE_URL='https://api.deepseek.com'
export DEEPSEEK_MODEL='deepseek-chat'
```

Do not commit keys.

If key is missing and `--planner llm` is requested, fail gracefully and save blocked/error artifact.

## Feishu optional environment

```bash
export FEISHU_APP_ID='...'
export FEISHU_APP_SECRET='...'
export FEISHU_FOLDER_TOKEN='...'
export FEISHU_ENABLE_WRITE=1
```

Real write requires `--confirm-write`.

Default behavior is dry-run only.
