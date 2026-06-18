# 05. Ariadne 功能优先级路线

Status: Updated by
[`ADR-0004`](../adr/ADR-0004-ticket-centered-agent-workbench.md).

本文件定义后续实施优先级。

## P0：必须补齐，才能让 Ariadne 成为大厂 Agent 岗项目

### P0-1：Ticket Backlog Update Loop

为什么重要：

```text
Multica 从 issue 开始，并让 agent 执行 issue。
Ariadne 必须让知识、反馈和代码状态持续改变 ticket 列表，再让 agent 执行 ticket。
```

交付：

```bash
ari ingest examples/sources/*.md --planner llm
ari ticket list
ari ticket assign ARI-003 --to codex --runtime-profile production
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari daemon run-once --confirm-execution
ari ticket comments ARI-003
ari export board
```

`fake-codex` 只用于测试和离线回归，不作为本路线的产品验收路径。

输出：

```text
新增 / 更新 / 降级 / supersede tickets
优先级变化
建议 Agent
依赖关系
验收标准
backlog update rationale
```

---

### P0-2：Knowledge / Feedback To Ticket Multi-Agent Flow

交付：

```text
Build Lead -> Research -> Knowledge -> Project Context -> Planner -> Ticket Updates
```

重点：

```text
不是 source type 固定映射
也不是 BuildGoal-first
而是基于 source + memory + repo context + review feedback 生成或更新 tickets
```

---

### P0-3：Build Team / Squad Routing

交付：

```bash
ari team list
ari ticket assign ARI-003 --to build-team
```

Build Lead 负责路由。

---

### P0-4：真实 Codex / Claude Code Teammate 产品路径

交付：

```bash
ari ticket assign ARI-003 --to codex
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari daemon run-once --confirm-execution
```

要求：

```text
真实调用 Codex
捕获 diff / tests
Reviewer 审查
Board 展示
失败时清晰 blocked
不能 fallback 到 fake-codex 假装成功
```

---

### P0-5：Provider Capability Matrix

交付：

```bash
ari backend matrix
ari backend doctor
```

展示每个 backend 能力差异。

---

## P1：增强工程深度

### P1-1：Skill Materialization

从 skill reference 升级到真正注入。

### P1-2：Memory Retrieval

Memory 要被 Planner 使用，而不只是写入。

### P1-3：Review / Eval Agent

增加语义 review、风险评分、验收标准对齐。

### P1-4：Project Resource Boundaries

扩展 local_directory 到 github_repo / feishu_space / memory_store 等资源。

---

## P2：产品化体验

### P2-1：Local Workbench UI

本地交互式 board。

### P2-2：Autopilot

定期 review / source triage / smoke test，并产生 ticket backlog updates。

### P2-3：Feishu preview / gated real write

生成 docs + tasks + decision log 的 preview plan，并在
`FEISHU_ENABLE_WRITE=1` 与 `--confirm-write` 同时存在时执行真实写入。

---

## 建议实施顺序

```text
Sprint A：架构修正 + Ticket backlog update loop
  ARI-015 Architecture Freeze correction
  ARI-016 Ticket Backlog Update Loop
  ARI-017 Knowledge / Feedback To Ticket Multi-Agent Flow

Sprint B：Agent Team 对齐 Multica
  ARI-018 Build Team / Squad Routing
  ARI-019 Provider Capability Matrix
  ARI-020 Skill Materialization

Sprint C：真实性与展示
  ARI-021 Real Codex / Claude Production Path
  ARI-022 Memory Retrieval
  ARI-023 Review / Eval Agent
  ARI-024 Offline Fixture Hardening
```
