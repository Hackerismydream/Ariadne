# ARI-013 — Evaluation, Demo Script, and Documentation Finalization

## 目标

把 Ariadne v1.0 从“代码能跑”整理成“能展示、能 review、能面试讲清楚”的项目。

## 需要实现

### 1. Evaluation report

新增：

```text
docs/evaluation/v1_0_evaluation.md
```

内容包括：

```text
测试命令
测试数量
主链路是否通过
fake-codex target project 是否被修改
review 是否通过
memory 是否写回
next tickets 是否生成
board 是否可展示
CodexBackend 是否 gated
ClaudeBackend 是否 gated
```

### 2. Demo script

新增：

```text
docs/demo/ARIADNE_V1_DEMO_SCRIPT.md
```

脚本要包含：

```bash
ari ingest examples/sources/*.md
ari ticket list
ari ticket assign ARI-003 --to fake-codex
ari daemon run-once
ari ticket comments ARI-003
ari runtime journal
ari export board
ari board serve
```

每一步写清楚“用户应该看到什么”。

### 3. Interview narrative

新增：

```text
docs/interview/PROJECT_NARRATIVE.md
```

用中文写，说明：

1. 这个项目解决什么问题。
2. 为什么不是普通 RAG。
3. 为什么不是重新造 Codex。
4. 为什么对标 Multica。
5. Ariadne 和 Multica 的差异。
6. Build Ticket / Assignment / Daemon / Review / Memory 的设计价值。
7. Agent 能力点。
8. 工程难点。
9. 已知限制和下一步。

### 4. Architecture diagram in text

不需要图片，用 Mermaid 或 ASCII 即可：

```text
Source -> Ticket -> Assignment -> Daemon -> Planner -> Backend -> Review -> Memory -> Board
```

写入 README 或 docs。

### 5. Release checklist

新增：

```text
docs/ops/V1_RELEASE_CHECKLIST.md
```

包括：

```text
pytest
ruff
demo path
agent teammate mode path
board path
safety gates
no secrets
known limitations
```

## 验收标准

1. README 有 v1.0 quickstart。
2. development_report 有 v1.0 总结。
3. demo script 可直接复制运行。
4. interview narrative 能独立解释项目。
5. evaluation report 记录真实测试结果。
6. release checklist 完整。

## 注意

不要只写宣传文案，要把真实限制写清楚：

```text
本地单 worker
JSON/JSONL persistence
无生产级 web UI
真实 Codex 需要本机环境
Feishu 真写入默认关闭
```
