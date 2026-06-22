# Ariadne Agent Execution Rules

## 执行前必读（按顺序，不允许跳过）

1. `README.md` — 产品定义和当前状态
2. `docs/adr/ADR-0004-ticket-centered-agent-workbench.md` — 架构决策
3. `docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md` — 核心循环
4. `docs/superpowers/plans/2026-06-22-multica-grade-workbench-execution-brief.md` — 执行 brief
5. `docs/superpowers/plans/2026-06-22-multica-grade-agent-team-workbench-rebuild-plan.md` — 主计划

## 当前执行阶段

Phase 6: Lifecycle Hardening and Execution Evidence

范围见 `docs/superpowers/plans/2026-06-22-phase6-handoff.md`。不要执行 Phase 7 的任何内容。

## 核心约束（违反任何一条必须停下来）

1. **Ticket-centered:** BuildTicket 是工作中心，Goal 只是输入，Issue 只是 BuildTicket 的产品投影
2. **No separate Issue persistence:** `/api/issues` 必须从 BuildTicket 投影，不得创建独立的 Issue 数据模型或存储
3. **Local-first:** Python runtime, single-user, JSON/JSONL/.ariadne 存储，不得引入 Go/Postgres/auth/workspace/billing
4. **No fake acceptance:** `fake-codex` 和 `demo full` 只用于 offline regression fixture，不得作为产品验收证据
5. **Evidence required:** 真实执行（Codex/Claude/Feishu/GitHub）必须有 evidence，失败必须产生 blocker + Inbox item

## 偏移检测

如果你发现自己在做以下任何事情，立即停止并报告 blocker：

- 设计 Goal-first runtime（Goal 驱动调度而非 Ticket 驱动）
- 新增独立 Issue persistence layer（Issue model, Issue table, Issue file）
- `/api/issues` 绕过 BuildTicket 直接读写
- `#issues` 展示所有历史 tickets 而非当前 project/version mainline issue set
- 删除 Delivery 信息导致看不到当前版本目标（应上移为 Context strip，不是删除）
- 页面按钮存在但没有真实 API action
- UI 读取 static fixture 当产品路径
- 引入 React Router 或其他路由库
- 拆分 App.tsx 为多文件路由系统（Phase 1 不做）
- 为了让 UI 能工作而自行创建 Phase 2+ 的 API endpoint
- 引入 Go/Postgres/auth/workspace/billing

## Phase 6 Scope

### 做

1. Orphan recovery：stale CLAIMED/RUNNING assignments 自动 requeue
2. Auto-retry：safe failure reasons（command_unavailable 等）自动 retry，max 2 次，用 metadata 追踪 retry_count
3. `TicketAssignment.requeue()` method（如果不存在）
4. Runs 页面：daemon 有 active assignment 时，polling `GET /api/assignments/{id}/events` 展示 progress
5. Issue Detail：active assignment 时 polling progress events
6. Issue Detail：execution results 增加 diff_artifact_path 链接、review verdict badge、blocked → inbox 链接
7. Inbox 页面：navigate 时 auto-refresh
8. 新增 orphan recovery + auto-retry 测试

### 不做

- 不实现 WebSocket（用 5s polling）
- 不引入新 npm 依赖
- 不实现跨 runtime orphan recovery
- 不实现 retry policy 配置 UI
- 不改 Sources / Plan Changes / Team 页面
- 不新增 API endpoint
- 不改 Issue board view

### 验收标准

1. `python3.11 -m pytest` — 全部通过
2. `ruff check .` — clean
3. `cd frontend/ariadne-workbench && npm run build` — success
4. Orphan recovery 测试：stale assignment 被 requeue + re-executed
5. Auto-retry 测试：safe failure → retry → 3rd fail stops
6. `#runs` 展示 assignment progress events
7. `#issues/{key}` 展示 progress polling + execution evidence 增强
8. 截图保存到 `docs/evidence/phase6-lifecycle-evidence/`

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
