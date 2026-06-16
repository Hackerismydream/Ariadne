# 05. Ariadne 功能优先级路线

本文件定义后续实施优先级。

## P0：必须补齐，才能让 Ariadne 成为大厂 Agent 岗项目

### P0-1：Build Goal

为什么重要：

```text
Multica 从 issue 开始。
Ariadne 必须从 goal 开始。
```

交付：

```bash
ari goal create "..."
ari goal attach-source GOAL-001 examples/*.md
ari goal plan GOAL-001
```

输出：

```text
多个 Build Tickets
优先级
建议 Agent
依赖关系
验收标准
```

---

### P0-2：Goal-to-Ticket Multi-Agent Flow

交付：

```text
Build Lead -> Research -> Knowledge -> Project Context -> Planner -> Tickets
```

重点：

```text
不是 source type 固定映射
而是基于 goal + source + memory + repo context 生成 tickets
```

---

### P0-3：Build Team / Squad Routing

交付：

```bash
ari team list
ari goal assign GOAL-001 --to build-team
```

Build Lead 负责路由。

---

### P0-4：真实 Codex Teammate 主 demo

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

定期 review / source triage / smoke test。

### P2-3：Feishu richer dry-run / gated real write

生成 docs + tasks + decision log 的 richer plan。

---

## 建议实施顺序

```text
Sprint A：架构冻结 + Build Goal
  ARI-015 Architecture Freeze
  ARI-016 Build Goal
  ARI-017 Goal-to-Ticket Multi-Agent Flow

Sprint B：Agent Team 对齐 Multica
  ARI-018 Build Team / Squad Routing
  ARI-019 Provider Capability Matrix
  ARI-020 Skill Materialization

Sprint C：真实性与展示
  ARI-021 Real Codex Main Demo
  ARI-022 Memory Retrieval
  ARI-023 Review / Eval Agent
  ARI-024 Demo Hardening
```

