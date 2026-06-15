# ARI-000 — Ariadne v1.0 完成契约

## 目标

本次 Sprint 的目标不是再做一个局部增强，而是把 Ariadne 做到可以被称为 **v1.0 MVP** 的状态。

v1.0 的定义是：

> Ariadne 是一个本地优先、Ticket 驱动的 Learning-to-Build Agent 工作台。用户可以把外部知识转成 Build Ticket，把 Ticket 分配给 Agent，本地 daemon 认领任务，Agent 通过真实或模拟 coding backend 修改目标项目，系统捕获日志、diff、测试结果，Reviewer 审查，Memory 写回，生成后续 Ticket，并在 Board 上展示完整协作过程。

## v1.0 必须展示的主链路

必须支持并通过以下路径：

```bash
ari ingest examples/sources/*.md
ari ticket list
ari ticket assign ARI-003 --to fake-codex
ari daemon run-once
ari ticket comments ARI-003
ari runtime journal
ari runtime recover
ari export board
```

同时保留直接执行路径：

```bash
ari ticket run ARI-003 --backend fake-codex
```

真实 Codex 路径必须作为一等 backend 存在，但默认受安全门控：

```bash
ari ticket assign ARI-003 --to codex
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari daemon run-once --confirm-execution
```

如果本机没有 Codex，必须清晰进入 blocked，而不是假装成功，也不能 fallback 到 fake-codex。

## v1.0 的最低验收标准

### 产品层

v1.0 不是“跑完 demo full”的系统，而是可复用工作台：

1. Ticket 可以被分配给 Agent。
2. Daemon 可以认领 Assignment。
3. Agent 会在 Ticket 下写进度、阻塞、review、memory 评论。
4. Runtime Journal 记录每个阶段。
5. 失败可以进入 retry / recovery 流程。
6. Board 能展示 Assignment、Comments、Journal、Handoff、Backend、Diff、Tests、Review、Memory、Next Tickets。
7. Codex backend 是真实可调用 scaffold，不是改名的 shell backend。
8. fake-codex 是安全测试 backend，但不能掩盖真实 backend 的缺失。
9. 上游 source ingestion / planner 能处理普通 markdown，而不是只识别固定 fixture。
10. README 中有一条完整 v1.0 使用路径。

### 工程层

1. 所有默认测试不依赖网络、真实 Codex、Claude、DeepSeek、Feishu、GitHub token。
2. 所有外部执行都必须同时需要环境变量和 CLI confirm flag。
3. 不允许 Ariadne 自动 commit / push / merge / create PR。
4. 所有运行状态必须持久化到 `.ariadne/`。
5. 所有关键阶段必须有 artifact 或 journal event。
6. 所有失败必须有 typed failure reason 或清晰 blocker。
7. `pytest` 和 `ruff check .` 必须通过。
8. `docs/development_report.md` 必须更新到 v1.0 状态。

## 本次 Sprint 包含的 ARI

本次 Sprint 请连续完成：

```text
ARI-007 — Daemon Supervision and Heartbeat
ARI-008 — Retry Queue and Safe Recovery
ARI-009 — Multi-Agent Handoff Loop
ARI-010 — Real Codex Teammate Backend
ARI-011 — Upstream Planner and Source-to-Ticket Intelligence
ARI-012 — Workbench Board and Local UX
ARI-013 — Evaluation, Demo Script, and Documentation Finalization
ARI-014 — Final Safety Gate and Release Readiness
```

不要每做完一个 ARI 就停下来问用户。请连续实现，最后统一报告。

## 交付策略

优先级顺序：

```text
可运行完整链路 > 可靠状态持久化 > 安全边界 > 测试覆盖 > Board 展示 > 文档 polish
```

如果时间不足，必须优先保证：

```text
assign -> daemon -> execution -> review -> memory -> next tickets -> board
```

不要优先做漂亮 UI 或大量文档。

## 绝对不要做

1. 不要重写整个项目。
2. 不要做完整 Multica clone。
3. 不要引入 Postgres / Go server / WebSocket / 多 workspace / 权限系统。
4. 不要让测试依赖外部服务。
5. 不要提交 secret。
6. 不要破坏已有 fake-codex 和 direct ticket run 路径。
7. 不要只做文档或 scaffold。

## 最终完成报告必须包含

1. 完成了哪些 ARI。
2. 每个 ARI 改了哪些文件。
3. 新增了哪些 CLI。
4. 主链路是否通过。
5. Codex backend 状态。
6. fake-codex 目标项目修改是否通过。
7. daemon / assignment / comments / journal / board 是否可见。
8. `pytest` 和 `ruff` 结果。
9. 已知限制。
10. 下一批 Build Tickets。
