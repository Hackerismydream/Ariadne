# Security and License Guidance

## Multica license caution

Multica uses a modified Apache-style license with additional conditions. Do not copy code.

Use Multica for:

```text
architecture study
conceptual mapping
domain-model inspiration
failure-mode analysis
lifecycle comparison
```

Do not:

```text
vendor Multica code
copy substantial source files
copy UI assets
copy frontend implementation
remove Multica logo/copyright if running Multica frontend
turn Ariadne into a hosted Multica-derived service
```

## Secrets

Do not commit:

```text
.env
.env.*
secrets/
*.secret
API keys
tokens
raw smoke-test output with secrets
```

## External execution

Real external execution must remain gated:

```text
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1
--confirm-execution
```

Feishu write must remain gated:

```text
FEISHU_ENABLE_WRITE=1
--confirm-write
```

## Local directory safety

Treat target repo execution as risky.

Before execution:

```text
validate target path
acquire directory lock
write route decision
write progress event
```

After execution:

```text
release lock
capture diff/tests
review
write memory/next tickets
```
