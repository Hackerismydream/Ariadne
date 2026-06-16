# ARI-018 Real Codex Teammate Main Demo

## 目标

把真实 Codex path 从 smoke / optional 变成 Ariadne 的核心可演示路径。

## 不能做

不能默认开启真实执行。
不能在未确认时调用 Codex。
不能 fallback fake-codex 假装成功。
不能 auto commit / push / merge / PR。

## CLI 主路径

```bash
ari ticket assign ARI-003 --to codex
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari daemon run-once --confirm-execution
```

## Codex command template

默认模板可以保持：

```text
codex exec --cd {target_repo} --prompt-file {handoff_file}
```

但需要兼容本地 Codex 的 stdin 模板：

```text
codex exec -c model_reasoning_effort="none" --cd {target_repo} - < {handoff_file}
```

## 必须实现

```text
codex command compatibility doctor
推荐模板诊断
handoff file 路径展示
Codex unavailable 时清晰 blocked
Codex gate unset 时清晰 blocked
Codex 执行成功后捕获 diff/tests/review/memory/board
```

## 验收

无 Codex / gate 未开时：

```bash
ari ticket assign ARI-003 --to codex
ari daemon run-once
```

应 blocked，不崩溃。

有 Codex 且 gate 开启时：

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 \
ARIADNE_CODEX_COMMAND_TEMPLATE='codex exec -c model_reasoning_effort="none" --cd {target_repo} - < {handoff_file}' \
ari daemon run-once --confirm-execution
```

应真实执行。

