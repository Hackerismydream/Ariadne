# ARI-010 — Real Codex Teammate Backend

## 目标

让真实 Codex 成为 Ariadne 的一等 Agent，而不是只有 fake-codex demo。

当前状态：

```text
fake-codex 是默认可运行 backend
codex backend 有安全门控和 smoke path
```

本轮要确保：

```text
ari ticket assign ARI-003 --to codex
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari daemon run-once --confirm-execution
```

这条路径是清晰、可诊断、可 blocked、可记录的。

## 安全原则

真实 Codex 默认关闭。

必须同时满足：

```text
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1
--confirm-execution
```

否则必须 blocked。

禁止：

```text
auto commit
auto push
auto merge
create PR
```

## CodexBackend 要求

### 1. Handoff 文件

每次执行前写：

```text
.ariadne/handoffs/<ticket_key_or_id>.md
```

内容必须包括：

```text
Ticket
Build Packet
Goal
Context
Allowed paths
Acceptance criteria
Test command
Safety constraints
Skills
No commit / push / PR
```

### 2. 命令模板

支持：

```text
ARIADNE_CODEX_COMMAND_TEMPLATE
```

默认：

```text
codex exec --cd {target_repo} --prompt-file {handoff_file}
```

支持变量：

```text
{target_repo}
{handoff_file}
{ticket_id}
{ticket_key}
{assignment_id}
{run_id}
```

### 3. Disabled path

如果未开启 gate，返回 blocked ExecutionResult：

```text
failure_reason = external_execution_blocked
block_reason = external execution disabled
```

如果 `codex` 不存在，返回：

```text
failure_reason = command_unavailable
block_reason = codex command unavailable
```

不能 fallback 到 fake-codex。

### 4. 执行结果

如果执行，则捕获：

```text
stdout
stderr
exit_code
started_at
ended_at
git status before / after
changed files
git diff
test command
test exit code
test stdout/stderr
```

### 5. Backend doctor

增强：

```bash
ari backend doctor
```

展示：

```text
codex command path
command template set?
external execution enabled?
confirm required?
```

不能输出 API key 或 secret。

## ClaudeCodeBackend

Claude backend 做同样 scaffold：

```text
ARIADNE_CLAUDE_COMMAND_TEMPLATE
```

默认：

```text
claude --print < {handoff_file}
```

要求同 Codex，但测试只覆盖 disabled / unavailable / command rendering，不要求真实 Claude。

## CLI 示例

README 必须加入：

```bash
ari ticket assign ARI-003 --to codex
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari daemon run-once --confirm-execution
```

以及如果本机没有 Codex：

```text
Assignment blocked: codex command unavailable
```

## 测试要求

测试覆盖：

1. CodexBackend 未开启 gate 时 blocked。
2. CodexBackend 无 command 时 blocked。
3. Codex command template 渲染正确。
4. Codex 不会 fallback 到 fake-codex。
5. assign to codex + daemon run-once 在 gate 未开时产生 blocker comment。
6. backend doctor 不泄露 secret。
7. ClaudeCodeBackend 同样 gated。

测试不能要求真实 Codex 安装。

## 可选 smoke

如果本机 Codex 可用且 gate 开启，可以运行 smoke，并把结果写到：

```text
docs/smoke_test_results/ARI-010-real-codex-teammate-summary.md
```

如果不可用，写明：

```text
Codex unavailable; disabled path tested.
```

## 完成标准

完成后，真实 Codex 作为 Agent teammate 的路径必须是“一等路径”：

```text
assign to codex
daemon claims
CodexBackend checks gate
handoff generated
execution blocked or executed
comments / journal / board show result
```
