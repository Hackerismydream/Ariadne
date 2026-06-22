# Ariadne Agent Execution Rules

## 执行前必读（按顺序，不允许跳过）

1. `README.md` — 产品定义和当前状态
2. `docs/adr/ADR-0004-ticket-centered-agent-workbench.md` — 架构决策
3. `docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md` — 核心循环
4. `docs/superpowers/plans/2026-06-22-multica-grade-workbench-execution-brief.md` — 执行 brief
5. `docs/superpowers/plans/2026-06-22-multica-grade-agent-team-workbench-rebuild-plan.md` — 主计划

## 当前执行阶段

Phase 4: Team, Runs, and Inbox Control Surfaces

范围见 `docs/superpowers/plans/2026-06-22-phase4-handoff.md`。不要执行 Phase 5-7 的任何内容。

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

## Phase 4 Scope

### 做

1. 扩展 `PageKey` 加入 `"team" | "runs" | "inbox"`，更新 routes.ts
2. Team 页面消费 `GET /api/team/agents` + `/api/team/build-teams` + `/api/team/skills`
3. Runs 页面消费 `GET /api/runs/runtimes` + `/api/runs/assignments` + `GET /api/daemon/status`
4. Runs 页面支持 Start/Stop Daemon（`POST /api/daemon/start` / `POST /api/daemon/stop`）
5. Inbox 页面消费 `GET /api/inbox`，支持 repair/rerun/acknowledge/resolve actions
6. Diagnostics 只保留技术诊断，不再承载 team/runs/inbox 内容
7. 所有已有 route 继续工作

### 不做

- 不改后端 Python 代码
- 不新增 API endpoint
- 不实现 agent 配置编辑（enable/disable、model selection）
- 不实现 daemon claim/heartbeat/retry/orphan recovery（Phase 6）
- 不实现 WebSocket
- 不引入新 npm 依赖
- 不动 Issues 页面
- 不动 Sources / Plan Changes 页面（Phase 5）

### 验收标准

1. `python3.11 -m pytest` — 全部通过
2. `ruff check .` — clean
3. `cd frontend/ariadne-workbench && npm run build` — success
4. `#team` 展示 agents、build teams、skills
5. `#runs` 展示 runtimes、assignments、daemon control（start/stop 调真实 API）
6. `#inbox` 展示 items，actions 调真实 API
7. 截图保存到 `docs/evidence/phase4-team-runs-inbox/`

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
