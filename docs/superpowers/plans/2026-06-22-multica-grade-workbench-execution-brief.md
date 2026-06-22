# Ariadne Multica 级 Workbench 执行 Brief

> **For agentic workers:** 先读本 brief，再读主计划。执行时必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`。不要一次性实施所有 phase；每次只执行一个可独立合并的 phase。

## 元数据

- **创建时间:** `2026-06-22 11:03:00 CST`
- **用途:** 防止 Codex 在执行 Multica-grade Workbench 重构时发生上下文偏移。
- **主计划:** `/Users/martinlos/code/Ariadne/docs/superpowers/plans/2026-06-22-multica-grade-agent-team-workbench-rebuild-plan.md`
- **目标:** 让 Ariadne 成为面向 AI Builder 的 local-first Agent Team Workbench：外部输入和反馈更新当前版本 issue set，agent team 通过 Python runtime 调度 Codex / Claude 执行目标项目，并把 evidence 回流到 Workbench。

## 执行前必须读

按顺序读，不允许跳过：

1. `/Users/martinlos/code/Ariadne/README.md`
   - 重点读：Production Product Path、Local API Control Plane、Multica Architecture Alignment、Ariadne v1.0 Architecture、Workbench Frontend。
2. `/Users/martinlos/code/Ariadne/docs/adr/ADR-0004-ticket-centered-agent-workbench.md`
   - 锁定：Goal 是输入，不是中心对象；BuildTicket 是工作中心。
3. `/Users/martinlos/code/Ariadne/docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md`
   - 锁定：`Knowledge / Feedback / Codebase -> Ticket backlog -> Agent -> Runtime -> Review / Memory -> Ticket backlog`。
4. `/Users/martinlos/code/Ariadne/docs/superpowers/plans/2026-06-22-multica-grade-agent-team-workbench-rebuild-plan.md`
   - 锁定：当前计划的 phase、出门门槛、Multica 对照实现笔记。
5. 当前 phase 对应的 Multica 文件：
   - Navigation / IA: `/Users/martinlos/code/multica/packages/views/layout/app-sidebar.tsx`
   - Issues: `/Users/martinlos/code/multica/packages/views/issues/components/issues-page.tsx`
   - Issues Board: `/Users/martinlos/code/multica/packages/views/issues/components/board-view.tsx`
   - Issue Detail: `/Users/martinlos/code/multica/packages/views/issues/components/issue-detail.tsx`
   - Agents: `/Users/martinlos/code/multica/packages/views/agents/components/agents-page.tsx`
   - Runtimes: `/Users/martinlos/code/multica/packages/views/runtimes/components/runtimes-page.tsx`
   - Lifecycle: `/Users/martinlos/code/multica/server/internal/handler/task_lifecycle.go`
   - Retry schema: `/Users/martinlos/code/multica/server/migrations/055_task_lease_and_retry.up.sql`
   - Daemon: `/Users/martinlos/code/multica/server/cmd/multica/cmd_daemon.go`
6. 当前 phase 对应的 Ariadne 代码入口：
   - Frontend shell: `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/App.tsx`
   - Frontend API client: `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/shared/api/client.ts`
   - Frontend API types: `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/shared/api/types.ts`
   - HTTP routes: `/Users/martinlos/code/Ariadne/ariadne_ltb/interfaces/http/routes.py`
   - Workbench projection: `/Users/martinlos/code/Ariadne/ariadne_ltb/application/workbench_projection.py`
   - Assignment services: `/Users/martinlos/code/Ariadne/ariadne_ltb/application/assign_ticket.py`
   - Run assignment service: `/Users/martinlos/code/Ariadne/ariadne_ltb/application/run_assignment.py`
   - Runtime status: `/Users/martinlos/code/Ariadne/ariadne_ltb/application/runtime_status.py`
   - Daemon control: `/Users/martinlos/code/Ariadne/ariadne_ltb/application/daemon_control.py`
   - Models: `/Users/martinlos/code/Ariadne/ariadne_ltb/models.py`

## 当前现实快照

执行前先确认这些现实仍成立；如果不成立，先更新本 brief 或主计划，不要盲改：

- 前端当前仍主要集中在 `frontend/ariadne-workbench/src/App.tsx`。
- 现有前端 route 仍有 `delivery / project / sources / tasks / ready / diagnostics`。
- README 当前仍说默认 Workbench screen 是 `Current Version Delivery`。
- 新方向不是删除 Delivery 信息，而是把它变成所有主页面顶部的 `Current Version Context`。
- 后端已有可用 API：
  - `GET /api/workbench`
  - `GET /api/runtime/status`
  - `GET /api/daemon/status`
  - `POST /api/daemon/start`
  - `POST /api/daemon/stop`
  - `GET/POST /api/target-projects`
  - `GET/POST /api/sources`
  - `POST /api/sources/{id}/analyze`
  - `POST /api/issue-factory/preview`
  - `POST /api/issue-factory/{id}/apply`
  - `POST /api/tickets/{id}/assign`
  - `POST /api/assignments/{id}/run`
  - inbox repair / rerun / acknowledge actions
- 新 `/api/issues*` 只能是现有 ticket / assignment / run / comment / artifact store 的 projection 或 action facade。

## 不可违反的执行约束

1. `Current Version Context` 是全局上下文，不是普通 Delivery 页面。
2. `#issues` 默认只展示当前 project/version mainline issue set。
3. `Issue` 只是 `BuildTicket` 的产品投影，不新建 issue store。
4. 所有新 API 必须投影现有 ticket / assignment / run / artifact / comment store。
5. UI 不允许把 static fixture 当产品数据。
6. `fake-codex`、`demo full`、offline fixture 不能作为产品验收。
7. 每个 phase 必须有浏览器 evidence，否则不算完成。
8. Codex / Claude / Feishu / GitHub 不能假装成功；没有 evidence artifact 就必须显示 blocked。
9. 不能引入 Go backend、Postgres、多租户 auth、hosted workspace、billing、remote runtime registry。
10. 不允许一次性重写全部前端；必须保留旧 route 兼容，按 phase 收敛。

## Phase 执行规则

每次只选一个 phase：

```text
Phase 1: product IA and current version context
Phase 2: multica-style API projections
Phase 3: issues workbench
Phase 4: team and runs control surfaces
Phase 5: source-to-plan-changes integration
Phase 6: lifecycle, inbox, execution evidence
Phase 7: browser dogfood closure evidence
```

每个 phase 的最小交付单位：

- 一个独立 commit。
- 可回滚。
- 有 focused tests。
- 前端受影响时 `npm run build` 通过。
- 有浏览器验收记录。
- 有 evidence artifact 或阶段报告。
- 不扩大 demo/fake/fixture product path。

## 上下文偏移检测

执行中如果出现以下任一情况，必须停止并修正方向：

- 开始设计 `BuildGoal` 或 Goal-first runtime。
- 新增独立 `Issue` persistence。
- 把 `/api/issues` 做成绕过 `BuildTicket` 的第二套 API。
- 让 `#issues` 展示所有历史 tickets，而不是 current project/version mainline issue set。
- 把 `Delivery` 完全删除，导致用户看不到当前项目版本目标。
- 继续让用户在 Delivery、Runs、Inbox、Artifacts 之间拼一个 issue 的事实。
- 页面按钮存在但没有真实 API action。
- 页面读取 `frontend/ariadne-workbench/src/data.ts` 或 static fixture 并当成产品路径。
- 用 `fake-codex` 或 `demo full` 证明真实产品闭环。
- 真实执行失败但没有 blocker id、Inbox item、Issue Detail evidence。
- 为了像 Multica 而引入 Go/Postgres/auth/workspace/billing。

## 必须保留的 Ariadne 产品语言

可以说：

```text
Ticket-centered Agent Workbench
Current Version Context
current project/version mainline issue set
Source Artifact
Issue Delta / Plan Changes
BuildTicket projection
Assignment
AgentRun
RouteDecision
HandoffPacket
Run Evidence
ReviewReport
Memory
Next Issue / Repair Issue
```

避免说：

```text
Goal-driven runtime
BuildGoal-first
global issues app
Multica clone
demo path
fake-codex product run
static board as product evidence
new Issue database
hosted workspace
```

## 每阶段最终报告格式

每个 phase 完成后，回复必须包含：

```text
Phase:
Branch:
Commit:
Files changed:
Tests run:
Browser evidence:
API evidence:
Artifacts:
Known blockers:
Rollback:
Whether this phase is independently mergeable:
Next phase:
```

如果没有浏览器 evidence，必须明确写：

```text
Not complete. Browser evidence missing.
```

## 允许的 blocked 完成状态

如果真实 Codex / Claude / Feishu / GitHub 因环境或 gate 不能执行，可以结束为 `product-visible blocked`，但必须满足：

- Issue Detail 可见 blocker。
- Inbox 可见 blocker。
- blocker 有 typed failure reason。
- blocker 有 repair / rerun / human action。
- dogfood 或阶段报告记录 exact blocker。
- 不声称真实执行成功。

## 推荐开始方式

先执行 Phase 1，不要直接跳 Phase 3。

Phase 1 的目标不是“重做漂亮 UI”，而是建立防偏移骨架：

```text
Current Version Context
  -> #issues default route
  -> scoped issue surface
  -> compressed navigation
  -> legacy route compatibility
```

如果 Phase 1 没把上下文固定住，后续 API 和 UI 都会继续散。
