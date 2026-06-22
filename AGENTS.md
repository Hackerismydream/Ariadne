# Ariadne Agent Execution Rules

## 执行前必读（按顺序，不允许跳过）

1. `README.md` — 产品定义和当前状态
2. `docs/adr/ADR-0004-ticket-centered-agent-workbench.md` — 架构决策
3. `docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md` — 核心循环
4. `docs/superpowers/plans/2026-06-22-multica-grade-workbench-execution-brief.md` — 执行 brief
5. `docs/superpowers/plans/2026-06-22-multica-grade-agent-team-workbench-rebuild-plan.md` — 主计划

## 当前执行阶段

Phase 1: Product IA and Current Version Context

范围见下方 Phase 1 Scope 章节。不要执行 Phase 2-7 的任何内容。

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

## Phase 1 Scope

### 做

1. 默认 hash route 从 `delivery` 改为 `issues`（修改 `useState<PageKey>` 初始值）
2. 新增 `CurrentVersionContext` 组件 — 固定在所有页面顶部的 persistent strip
   - 数据来源：现有 `GET /api/workbench` 返回的 `currentVersionDelivery`
   - 展示字段：Project, Target Version, Goal, Sources readiness, Issue Delta status, Active Run, Blocked count, Latest Evidence, Next Action
3. 左侧导航 label 更新为：Issues, Sources, Plan Changes, Team, Runs, Inbox, Diagnostics
4. `delivery` 页面内容整合进 `CurrentVersionContext` strip，`#delivery` hash 重定向到 `#issues`
5. 更新 README 默认路由描述
6. 所有现有测试继续通过（pytest 399 passed, ruff clean, npm run build success）

### 不做

- 不新增 API endpoint
- 不拆分 App.tsx 为多文件路由系统
- 不引入 React Router 或任何新前端依赖
- 不创建新的 Issue 数据模型
- 不改后端 Python 代码（除非修复 existing API response 不足以支持 Context strip 的字段）
- 不实现 Phase 2-7 的任何功能

### PageKey 映射表

当前 -> Phase 1 后：

| 当前 PageKey | Phase 1 后 | 说明 |
|---|---|---|
| `delivery` | 删除（重定向到 `issues`） | 内容上移为 CurrentVersionContext strip |
| `project` | 保持 | 暂不改动 |
| `sources` | 保持 | 暂不改动 |
| `tasks` | 改名 `plan-changes` | label 改，hash 兼容 |
| `ready` | 改名 `issues` | 成为默认页，hash `#issues` 已有 legacyMap 支持 |
| `diagnostics` | 保持 | Phase 3+ 再拆分为 team/runs/inbox/diagnostics |

### 验收标准

1. 浏览器打开 `http://127.0.0.1:8766/` 默认显示 issues 页面
2. 页面顶部有 CurrentVersionContext strip，展示当前版本核心信息
3. 左侧导航显示新 label
4. `#delivery` 自动跳转到 `#issues`
5. `python3.11 -m pytest` — 全部通过
6. `ruff check .` — clean
7. `cd frontend/ariadne-workbench && npm run build` — success
8. 截图证明以上 1-4 成立

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
