# Ariadne Agent Execution Rules

## 执行前必读（按顺序，不允许跳过）

1. `README.md` — 产品定义和当前状态
2. `docs/adr/ADR-0004-ticket-centered-agent-workbench.md` — 架构决策
3. `docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md` — 核心循环
4. `docs/superpowers/plans/2026-06-22-multica-grade-workbench-execution-brief.md` — 执行 brief
5. `docs/reviews/grill-workflows/results/2026-06-24-final-41-grill-list.md` — 当前问题清单
6. `docs/superpowers/plans/2026-06-24-grill-closure-campaign-plan.md` — 当前执行计划
7. `docs/superpowers/plans/2026-06-22-multica-grade-agent-team-workbench-rebuild-plan.md` — 历史主计划和 Multica 对照笔记

## 当前执行阶段

Grill Closure Campaign

范围见：

```text
docs/superpowers/plans/2026-06-24-grill-closure-campaign-plan.md
docs/reviews/grill-workflows/results/2026-06-24-final-41-grill-list.md
```

Phase 8: Knowledge Orchestration Layer 已完成为当前产品的一部分，但不再是
当前唯一执行边界。后续工作必须优先把 41 个 grill findings 收敛为真实浏览器产品闭环：

```text
Sources
  -> Current Issue Delta
  -> Current Issue Set
  -> Assignment
  -> Runtime Run
  -> Evidence
  -> Review / Memory / Next Issues
  -> Version Progress
```

旧 Phase 8 handoff 仍可作为知识层参考：

```text
docs/superpowers/plans/2026-06-23-phase8-knowledge-orchestration-handoff.md
docs/superpowers/plans/2026-06-23-phase8-langgraph-handoff.md.superseded
docs/adr/ADR-0005-langgraph-source-to-issue-pipeline.md
```

## 核心约束（违反任何一条必须停下来）

1. **Ticket-centered:** BuildTicket 是工作中心，Goal 只是输入，Issue 只是 BuildTicket 的产品投影
2. **No separate Issue persistence:** `/api/issues` 必须从 BuildTicket 投影，不得创建独立的 Issue 数据模型或存储
3. **Local-first:** Python runtime, single-user, JSON/JSONL/.ariadne 存储，不得引入 Go/Postgres/auth/workspace/billing
4. **No fake acceptance:** `fake-codex` 和 `demo full` 只用于 automated tests / offline regression harness，不得作为产品验收证据
5. **Evidence required:** 真实执行（Codex/Claude/Feishu/GitHub）必须有 evidence，失败必须产生 blocker + Inbox item
6. **No mock product data:** 落地的产品代码、Workbench、API projection、CLI product path、agent/runtime/orchestrator 不允许使用 mock / fixture / sample / static fallback 数据。所有产品数据必须来自真实用户输入、外部 source、目标代码库扫描、agent run、review、memory、或 `.ariadne` 持久化 store。Mock/fixture 数据只允许出现在 automated tests、test fixtures、或明确的离线回归测试 harness 中，且不能被产品路径读取。

## 偏移检测

如果你发现自己在做以下任何事情，立即停止并报告 blocker：

- 设计 Goal-first runtime（Goal 驱动调度而非 Ticket 驱动）
- 新增独立 Issue persistence layer（Issue model, Issue table, Issue file）
- `/api/issues` 绕过 BuildTicket 直接读写
- 在 Layer 2 之外新建持久化 wiki / markdown 文件
- 把 ProjectKnowledge 暴露成 HTTP API
- 在当前 campaign 内把 ProjectKnowledge 暴露成原始 CRUD HTTP API
- 在当前 campaign 内实现 Query / Lint / Memory，除非有新的批准计划
- `#issues` 展示所有历史 tickets 而非当前 project/version mainline issue set
- 删除 Delivery 信息导致看不到当前版本目标（应上移为 Context strip，不是删除）
- 页面按钮存在但没有真实 API action
- UI 读取 static fixture 当产品路径
- 在产品代码中新增 mock / fixture / sample / static fallback 数据
- 让 Workbench、API、CLI、agent runtime 从测试 fixture、hardcoded sample、前端内置数据、`web_data` snapshot、或假默认对象读取产品状态
- 为了让 UI 能工作而绕过 BuildTicket/Assignment/Artifact store 自行创建第二套 product state
- 引入 Go/Postgres/auth/workspace/billing

## Grill Closure Campaign Scope

### 做

1. 修复 Truth Layer：统一 current work / terminal verdict / evidence validity。
2. 修复 Runtime Control：assignment 唯一性、attempt lineage、scoped daemon claim、canonical blocker、Inbox allowed actions。
3. 修复 Issue Detail / Evidence Center：让单个 issue 页面成为事实中心，证据可打开且语义有效。
4. 修复 Knowledge-to-Issue：current issue delta、compiler provenance、target codebase snapshot、source artifact quality、claim-level evidence。
5. 建立 Browser Dogfood Closure Ledger：只在真实浏览器闭环推进目标项目版本时标记 `REAL_CLOSED`。

### 不做

- 不新增独立 Issue persistence。
- 不把 `/api/issues` 做成绕过 BuildTicket 的第二套 work store。
- 不引入 Go/Postgres/auth/workspace/billing。
- 不把 fake-codex、demo full、dry-run、CLI-only run 当成产品验收。
- 不使用 mock/static fixture/sample data 作为 Workbench 或 API 产品数据。
- 不暴露 ProjectKnowledge 原始 CRUD HTTP API；只能通过产品投影展示 provenance/evidence。
- 不先做 board drag/drop、sidebar polish、视觉改版，除非当前 phase 明确要求。

### 验收标准

1. `python3.11 -m pytest` — 全部通过或 phase 文档列出确切 blocker。
2. `ruff check .` — clean。
3. `cd frontend/ariadne-workbench && npm run build` — 前端受影响时必须通过。
4. 每个 phase 必须有浏览器 evidence。
5. P0 修复不得依赖 fake-codex、demo full、mock data、static fixture、CLI-only path。
6. 如果真实 Codex/Claude 执行被环境阻塞，必须显示为 `BLOCKED_WITH_EVIDENCE`，并写入 Issue Detail + Inbox + closure ledger；不得声称闭环。

## Multica 参考说明

Multica 源码位于 `/Users/martinlos/code/multica/`，不在本项目目录内。执行时：

- 如果你能访问该路径，按 execution brief 指定的文件列表读取参考
- 如果你不能访问该路径，不要报错或跳过——主计划中已包含 "Multica 对照实现笔记" 章节，直接使用该章节的摘要即可
- 不要因为无法读取 Multica 源码而偏离计划方向

关键 Multica 机制已内化到主计划：

- Persistent context（对应 CurrentVersionContext strip）
- Scoped issue board（对应 #issues 只展示当前 version mainline）
- Issue detail 事实中心（Phase 3）
- Execution log / shared task snapshot（Phase 4）
- Claim / heartbeat / retry / orphan recovery（Phase 6）
