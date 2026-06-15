# ARI-012 — Workbench Board and Local UX

## 目标

让 Ariadne 的展示更像工作台，而不是静态 artifact dump。

不要求做复杂 Web app，但 v1.0 需要一个可展示的本地 Board 体验。

## 当前状态

已有：

```text
ari export board
.ariadne/board/index.md
.ariadne/board/index.html
```

但还需要更清楚地展示：

```text
Agent 队友
Assignment
Handoff
Daemon
Journal
Retry
Codex gate
Next tickets
```

## 需要实现

### 1. Board 信息架构

Board 顶部增加：

```text
Ariadne v1.0 Workbench
```

包含：

```text
System Summary
Agent Queue
Tickets by Status
Active Assignments
Daemon / Runtime
Agent Comments
Recent Journal Events
Executed Tickets
Next Tickets
Backend Capability
Safety Gates
```

### 2. Ticket detail 区块

每个 Ticket 下展示：

```text
source
build packet
quality score
assigned agent
assignment status
handoff chain
backend
execution result
diff / changed files
test result
review verdict
memory path
feishu plan
next tickets
comments
journal events
retry chain
```

### 3. Local board serve

新增：

```bash
ari board serve
```

可以用 Python 标准库 `http.server`。

不需要 FastAPI。

行为：

```bash
ari board serve --port 8765
```

默认服务 `.ariadne/board/`。

### 4. Command UX

确保常用命令输出清晰：

```bash
ari agent list
ari ticket list
ari ticket show ARI-003
ari ticket comments ARI-003
ari daemon status
ari runtime recover
```

输出要让人能理解当前状态，不要只打印 JSON id。

### 5. Human handoff checklist

新增或更新：

```text
docs/ops/HUMAN_DEMO_SCRIPT.md
```

内容是一段 3-5 分钟 demo 脚本：

```bash
ari ingest examples/sources/*.md
ari ticket list
ari ticket assign ARI-003 --to fake-codex
ari daemon run-once
ari ticket comments ARI-003
ari export board
ari board serve
```

并说明面试时如何讲。

## 验收标准

测试覆盖：

1. `ari export board` 生成 md/html。
2. Board 包含 Agent Queue / Assignment / Handoff / Journal / Retry / Backend Gate。
3. `ari board serve --port 0` 或可测试启动逻辑。
4. CLI 输出包含可读状态。
5. 不引入必须的 Web 框架依赖。

## 文档要求

README 增加：

```bash
ari export board
ari board serve
```

说明这是本地只读 board。
