# ARI-019 Provider Capability Matrix

## 目标

把 backend doctor 升级为 Provider Capability Matrix。

## 背景

大厂 Agent 平台需要知道不同 coding backend 的能力差异，而不是只检查命令是否存在。

## 数据模型

新增或增强：

```text
ProviderCapability
ProviderCapabilityMatrix
ProviderDiagnostic
```

字段：

```text
backend_name
available
command_path
supports_prompt_file
supports_stdin
supports_session_resume
supports_mcp
skill_materialization_strategy
supports_model_selection
supports_reasoning_effort
supports_timeout
supports_diff_capture
supports_test_capture
requires_confirmation
requires_external_execution_gate
recommended_command_template
known_limitations
last_checked_at
```

## CLI

新增：

```bash
ari backend matrix
ari backend diagnose codex
ari backend diagnose claude-code
```

## Board

Board 展示 capability matrix。

## 验收

```bash
ari backend matrix
ari backend diagnose codex
ari doctor v1
```

不得打印 secret。

