# Ariadne Multica 级 Agent Team Workbench 重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 按任务逐项实施本计划。所有实施步骤使用 checkbox (`- [ ]`) 追踪，不允许跳过阶段出门门槛。

## 计划元数据

- **计划时间戳:** `2026-06-22 10:44:08 CST`
- **最后更新:** `2026-06-22 10:44:08 CST`
- **目标版本:** Ariadne v1.x Multica-grade local Agent Team Workbench
- **执行分支建议:** `codex/multica-grade-workbench-rebuild`
- **执行对象:** 后续 Codex / Ariadne implementation agent
- **评审来源:** 3 个 subagent 并行评审，覆盖产品心智、架构边界、执行验收
- **禁止口径:** 不允许把 Ariadne 继续做成 demo dashboard、fixture board、fake-codex-first、CLI-only 工具、或裸 Multica clone

## 目标

把 Ariadne 重构成面向 AI Builder 的本地 Agent Team Workbench：

```text
用户选择本地项目和目标版本
  -> 添加外部输入：博客、GitHub repo、论文、本地文档、当前代码库
  -> Ariadne 读取输入并生成 typed source artifacts
  -> Ariadne 根据项目目标、外部输入、代码库状态生成 issue delta
  -> 用户确认当前版本 issue set
  -> Build Lead 选择 Codex / Claude / Reviewer / Human 路由
  -> Python daemon claim assignment
  -> Codex / Claude 真执行目标项目
  -> diff / tests / review / memory / next issue / blocker 回流到 Workbench
  -> 当前版本状态更新
```

一句话：

```text
Multica 提供 issue/agent/runtime/workbench 的产品骨架；
Ariadne 在上层增加 source / feedback / codebase -> issue delta 的能力；
runtime 保持 Python local-first。
```

## 这次评审后修正的关键判断

原计划方向正确，但有三个问题必须修正：

- `#issues` 可以成为默认操作面，但不能是裸全局 issue board；它必须默认 scoped 到当前 project/version 的 mainline issue set。
- `Delivery` 不能继续做默认报告页，也不能被降成无关 summary；它应该变成所有页面顶部固定的 `Current Version Context`。
- `Issue` 只能是现有 `BuildTicket` 的产品投影和 UI 语言，不能引入第二套持久化模型、第二套 backlog、第二套状态机。

因此，本计划的核心产品结构是：

```text
Current Version Context
  + Issues Workbench
  + Sources
  + Plan Changes / Issue Delta
  + Team
  + Runs
  + Inbox
  + Diagnostics
```

不是：

```text
一堆并列页面
  + 一个报告页
  + 一个全局 ticket board
```

---

## 边界契约

实施前必须接受这些边界。违反任一条，都算计划偏航。

- [ ] Ariadne v1.x 仍然是 local-first、single-user、本地文件存储产品。
- [ ] runtime / daemon 必须保持 Python 实现。
- [ ] 不 fork Multica。
- [ ] 不迁移到 Go backend、Postgres、multi-tenant auth、hosted SaaS、workspace billing、远程 runtime registry。
- [ ] `Issue` 是 `BuildTicket` 的产品投影，不新增独立 issue persistence。
- [ ] `/api/issues*` 是现有 ticket / assignment / comment / artifact service 的 projection 或 action facade。
- [ ] `.ariadne` 存储结构不得破坏性迁移；新增字段必须兼容旧数据。
- [ ] `fake-codex` 只能作为测试、离线 fallback、debug fixture，不进入产品默认路径。
- [ ] `demo full` 只能作为 regression fixture，不进入产品验收主线。
- [ ] Codex / Claude / Feishu / GitHub 真实执行不能被假装成功；没有 evidence artifact 就只能记录 blocked。
- [ ] 浏览器路径必须成为每阶段验收的一部分，不能只靠测试和 build。

---

## 核心产品 Spine

所有页面、API、agent role 都必须服务这条 spine：

```text
Project Goal + Target Version
  -> Sources
  -> Typed Source Artifacts
  -> Issue Delta
  -> Confirmed Current Issue Set
  -> Route Decision
  -> Handoff Packet
  -> Assignment
  -> Codex / Claude Run
  -> Run Evidence
  -> Review
  -> Memory
  -> Next Issue / Repair Issue / Version Progress
```

每个 agent role 必须有明确 artifact 或 state transition：

| Agent Role | 输入 | 输出 |
| --- | --- | --- |
| Knowledge Agent | URL / 论文 / markdown / note | `KnowledgeArtifact` |
| Repo Understanding Agent | GitHub repo / local repo / codebase scan | `RepositoryUnderstandingArtifact` / `CodebaseStateArtifact` |
| Issue Factory Agent | goal + source artifacts + codebase state | `IssueDelta` |
| Build Lead Agent | confirmed issue + runtime capability | `RouteDecision` |
| Handoff Agent | issue + evidence + route decision | `HandoffPacket` / `handoff.md` |
| Runtime Agent / Daemon | assignment + backend capability | `AgentRun` / progress events |
| Codex / Claude Backend | handoff + target repo | changed files / diff / stdout / stderr / exit code |
| Reviewer Agent | diff + tests + acceptance criteria | `ReviewReport` |
| Memory Agent | run result + review + blockers | memory record + next issue suggestions |

如果某个页面或 API 不能说明自己在这条 spine 的位置，就不应该作为一级产品入口。

---

## 目标信息架构

一级导航压缩为 7 个入口，避免继续做成功能展台：

```text
Issues       当前版本主线 issue board / list / detail
Sources      外部输入、typed artifacts、分析状态
Plan Changes 外部输入和反馈导致的 issue delta；内部仍可叫 Issue Factory
Team         Agents / Build Teams / Skills
Runs         Runtime / daemon / assignment / execution evidence
Inbox        blockers / repair / rerun / human-needed
Diagnostics  product doctor / integration evidence / environment
```

`Current Version Context` 不是普通页面，而是所有主页面顶部固定区域：

```text
Project: <name>
Target Version: v0.1
Goal: <one-line goal>
Sources: ready / analyzing / failed
Issue Delta: applied / stale / needs review
Active Run: issue key + backend + status
Blocked: count + top blocker
Latest Evidence: diff/tests/review timestamp
Next Action: add source / review plan changes / assign issue / start runtime / fix blocker
```

默认 route：

```text
http://127.0.0.1:8766/#issues
```

但 `#issues` 必须默认展示当前 project/version 的 mainline issue set，历史 repair / old ARI/MCA issues 默认折叠到 Inbox 或 History。

---

## Multica 参考文件

实施每个对应 surface 前必须直接看这些文件，不靠记忆：

- `/Users/martinlos/code/multica/packages/views/layout/app-sidebar.tsx`
- `/Users/martinlos/code/multica/packages/views/issues/components/issues-page.tsx`
- `/Users/martinlos/code/multica/packages/views/issues/components/board-view.tsx`
- `/Users/martinlos/code/multica/packages/views/issues/components/issue-detail.tsx`
- `/Users/martinlos/code/multica/packages/views/agents/components/agents-page.tsx`
- `/Users/martinlos/code/multica/packages/views/runtimes/components/runtimes-page.tsx`
- `/Users/martinlos/code/multica/server/migrations/055_task_lease_and_retry.up.sql`
- `/Users/martinlos/code/multica/server/internal/handler/task_lifecycle.go`
- `/Users/martinlos/code/multica/server/cmd/multica/cmd_daemon.go`

借鉴内容：

- issue board / issue detail 的产品组织方式
- assignee / status / priority / runtime / progress 的展示方式
- agent 和 runtime 的可见能力面
- daemon lifecycle、heartbeat、retry、orphan recovery 的语义

不借鉴内容：

- Go server 作为 Ariadne runtime
- Postgres-backed workspace service
- hosted auth / billing / multi-tenant workspace
- Multica 的完整 schema 和部署模型

---

## 统一阶段出门门槛

每个阶段完成时必须满足：

- [ ] 自动测试通过，至少包含该阶段新增/修改的 focused tests。
- [ ] `ruff check .` 通过，除非明确记录现有遗留问题且本阶段未扩大问题。
- [ ] 前端受影响时，`npm run build` 通过。
- [ ] 浏览器路径验收通过，并记录 URL、步骤、截图或 trace 路径。
- [ ] 真实 local API 或真实 `.ariadne` store smoke 通过；不能只用 fixture DTO。
- [ ] 生成或更新 evidence artifact，路径写入阶段报告。
- [ ] 如果真实 Codex / Claude 未执行，必须记录 exact blocker，不允许声称成功。
- [ ] 如果出现 blocker，必须在 Issue Detail 和 Inbox 可追踪到同一个 blocker id。
- [ ] 本阶段 commit hash 记录到阶段报告。
- [ ] rollback 方式明确：revert commit、保留 legacy route、或 feature flag。

禁止进入下一阶段的情况：

- [ ] 只通过 build，没有浏览器验收。
- [ ] 只新增页面，但页面仍读 mock/static fixture。
- [ ] 只新增 API，但产品路径仍无法走通。
- [ ] 真实执行失败但没有 blocker evidence。
- [ ] `Issue` 和 `BuildTicket` 出现两套独立存储。

---

## API 迁移矩阵

新增 Multica-style API 前，必须写清楚旧接口如何兼容。

| 现有接口 | 新产品投影 / 动作 | 所属 service | 兼容要求 |
| --- | --- | --- | --- |
| `GET /api/workbench` | legacy aggregate only | `workbench_projection.py` | 保留到新页面稳定；不新增依赖 |
| `GET /api/tickets/*` | `GET /api/issues/*` | ticket / issue projection service | `Issue == BuildTicket projection` |
| `POST /api/tickets/{id}/assign` | `POST /api/issues/{id}/assign` | assignment service | 两者写同一 assignment store |
| `POST /api/assignments/{id}/run` | `POST /api/issues/{id}/run-now` 或 Runs action | assignment runner | 不创建第二套 execution |
| `GET /api/assignments/{id}/events` | issue detail / runs events | progress events service | 同一 events source |
| `GET /api/tickets/{id}/timeline` | `GET /api/issues/{id}/timeline` | timeline/comment service | timeline 口径一致 |
| inbox action routes | `GET /api/inbox` + actions | inbox service | actions 必须回写 issue/blocker |
| `GET /api/runtime/status` | `GET /api/runtimes` / `GET /api/agent-task-snapshot` | runtime capability service | runtime truth model 唯一 |

Phase 2 必须把这个矩阵变成测试或文档化 contract，避免 routes.py 变成双 API 面。

---

## Phase 1：产品语言、Current Version Context、导航骨架

**目标:** 先修用户心智。Ariadne 打开后看起来应该是“我正在推进这个项目版本”，不是“我在看一堆系统页面”。

**推进的 spine 段落:**

```text
Project Goal + Target Version -> Current Version Context -> Issues
```

**主要文件:**

- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/App.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/styles.css`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/types.ts`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/shared/api/types.ts`
- `/Users/martinlos/code/Ariadne/docs/architecture/ariadne_multica_grade_workbench_architecture.md`
- `/Users/martinlos/code/Ariadne/README.md`

**实施步骤:**

- [ ] 新增 `docs/architecture/ariadne_multica_grade_workbench_architecture.md`，写明本计划的产品骨架和边界契约。
- [ ] 保留旧 hash 兼容，先新增 route alias，不删除旧 route。
- [ ] 默认 route 改为 `#issues`，但页面顶部必须显示 `Current Version Context`。
- [ ] 把一级导航压缩为：
  - [ ] `Issues`
  - [ ] `Sources`
  - [ ] `Plan Changes`
  - [ ] `Team`
  - [ ] `Runs`
  - [ ] `Inbox`
  - [ ] `Diagnostics`
- [ ] 把 `Agents / Build Teams / Skills` 收敛进 `Team`。
- [ ] 把 `Runtimes / Assignment / Execution Evidence` 收敛进 `Runs`。
- [ ] `Delivery` 不作为默认 route；其信息变成顶部 current version context。
- [ ] 移除主路径中 `demo full`、`fake-codex`、fixture-first 文案。
- [ ] 不在本阶段重写后端逻辑，只修 shell、route、文案、上下文结构。

**浏览器验收:**

- [ ] 打开 `http://127.0.0.1:8766/#issues`。
- [ ] 5 秒内能看懂：当前项目、目标版本、当前主线 issue、下一步动作、运行/阻塞状态。
- [ ] 打开旧 hash 时不崩溃，并能引导到新导航。
- [ ] 页面不能出现“这是 demo / fake-codex 默认路径 / 静态 fixture 数据”的产品主线文案。

**命令:**

```bash
cd /Users/martinlos/code/Ariadne/frontend/ariadne-workbench
npm run build
```

---

## Phase 2：Multica-style API Projection，不新增第二套模型

**目标:** 前端不再从巨型 `/api/workbench` 反推页面状态；新增按页面组织的 read models，但全部投影现有 store。

**推进的 spine 段落:**

```text
Confirmed Current Issue Set -> Issue Detail / Team / Runs / Inbox projections
```

**主要文件:**

- `/Users/martinlos/code/Ariadne/ariadne_ltb/interfaces/http/routes.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/workbench_issues.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/workbench_issue_detail.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/workbench_agents.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/workbench_runtimes.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/workbench_projects.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/workbench_inbox.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/workbench_task_snapshot.py`
- `/Users/martinlos/code/Ariadne/tests/test_multica_grade_workbench_api.py`
- `/Users/martinlos/code/Ariadne/tests/test_frontend_api_contract_static.py`

**新接口:**

```text
GET    /api/issues
GET    /api/issues/{issue_id_or_key}
PATCH  /api/issues/{issue_id_or_key}
POST   /api/issues/{issue_id_or_key}/comments
GET    /api/issues/{issue_id_or_key}/timeline
POST   /api/issues/{issue_id_or_key}/assign
POST   /api/issues/{issue_id_or_key}/rerun
POST   /api/issues/{issue_id_or_key}/run-now
GET    /api/inbox
GET    /api/agent-task-snapshot
GET    /api/projects
GET    /api/projects/{project_id}
GET    /api/team/agents
GET    /api/team/build-teams
GET    /api/team/skills
GET    /api/runs/runtimes
GET    /api/runs/assignments
```

**实施步骤:**

- [ ] 增加 `IssueListItem` projection：`id`、`key`、`title`、`status`、`priority`、`assignee`、`project`、`targetVersion`、`sourceCount`、`evidenceCount`、`lastRunStatus`、`reviewVerdict`、`blockedReason`、`updatedAt`。
- [ ] 增加 `IssueDetail` projection：body、evidence、source links、route decision、handoff、comments、timeline、assignments、execution results、review、diff/tests summary、next issue links。
- [ ] 增加 `CurrentVersionContext` projection：当前项目、目标版本、goal、sources 状态、issue delta 状态、active run、blocked count、latest evidence、next action。
- [ ] 增加 `InboxListItem` projection：blocker id、issue key、failure reason、severity、action type、createdAt、resolution status。
- [ ] 增加 `AgentTaskSnapshot` projection：active assignment、queued count、blocked count、heartbeat、current issue key、backend、last event。
- [ ] 增加 `RuntimeListItem` projection：daemon state、external execution capability、Codex availability、Claude availability、queue depth、active assignment。
- [ ] 增加 `AgentListItem` projection：agent role、backend、runtime compatibility、active assignment count、blocked count、configuration fields。
- [ ] `/api/workbench` 保留为 legacy aggregate，不让新页面继续扩大依赖。
- [ ] `routes.py` 只做薄路由；projection 逻辑进入 `ariadne_ltb/application/workbench_*`。
- [ ] 添加 old endpoint -> new projection 的兼容测试。
- [ ] Phase 2 必须用真实 local API smoke，不只跑 fixture contract test。

**浏览器 / HTTP 验收:**

- [ ] 启动 Ariadne local API。
- [ ] 用真实 `.ariadne` store 或临时真实 project store 请求：
  - [ ] `GET /api/issues`
  - [ ] `GET /api/inbox`
  - [ ] `GET /api/runs/runtimes`
  - [ ] `GET /api/team/agents`
  - [ ] `GET /api/projects`
- [ ] 保存响应样例到 evidence 目录。
- [ ] 确认响应里没有 mock/static fixture 标记。

**命令:**

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m pytest \
  tests/test_multica_grade_workbench_api.py \
  tests/test_control_plane_http.py \
  tests/test_workbench_daemon_feedback.py \
  tests/test_frontend_api_contract_static.py
ruff check .
```

---

## Phase 3：Issues Workbench 重构

**目标:** 把 Ariadne 的主工作面做成当前版本 issue board / list / detail，而不是内部模块目录。

**推进的 spine 段落:**

```text
Confirmed Current Issue Set -> Issue Board -> Issue Detail -> Next Action
```

**主要文件:**

- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/App.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/app/routes.ts`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/app/shell/AppShell.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/issues/IssuesPage.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/issues/IssueBoard.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/issues/IssueList.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/issues/IssueDetail.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/widgets/current-version/CurrentVersionStrip.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/widgets/issue-detail/IssueActivity.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/widgets/issue-detail/IssueEvidence.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/widgets/issue-detail/IssueExecution.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/widgets/issue-detail/IssueComments.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/shared/api/client.ts`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/shared/api/types.ts`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/styles.css`

**实施步骤:**

- [ ] 分阶段抽离 `App.tsx`：route alias -> shell extraction -> page extraction -> legacy cleanup。
- [ ] `IssuesPage` 默认只展示当前 project/version mainline issue set。
- [ ] repair / historical issues 默认不混入主 board；通过 Inbox/History 进入。
- [ ] Board columns：Backlog、Ready、Assigned、Running、Review、Blocked、Done。
- [ ] Issue card 显示：key、title、priority、assignee/backend、run state、review state、evidence count、blocked marker。
- [ ] Issue detail route：`#issues/<issue_key_or_id>`。
- [ ] Issue detail 必须展示完整链路：
  - [ ] issue 目标和验收标准
  - [ ] source evidence
  - [ ] route decision
  - [ ] handoff packet
  - [ ] assignment 和 active run
  - [ ] progress events
  - [ ] changed files / diff summary
  - [ ] tests
  - [ ] review verdict
  - [ ] comments / timeline
  - [ ] blocker / repair / next issue
- [ ] Primary actions：assign、run now、rerun、add comment、open target project、open evidence。
- [ ] Empty state 只能指向真实产品动作：add source、review plan changes、start runtime、assign issue。

**浏览器验收:**

- [ ] 打开 `http://127.0.0.1:8766/#issues`，看到当前版本 issue board。
- [ ] 打开 `http://127.0.0.1:8766/#issues/ARI-003` 或当前 store 中真实 issue key。
- [ ] 用户能判断：这个 issue 为什么存在、由哪些 source 支撑、下一步谁来做、运行证据在哪里。
- [ ] 页面没有静态 mock 数据。

**命令:**

```bash
cd /Users/martinlos/code/Ariadne/frontend/ariadne-workbench
npm run build
```

---

## Phase 4：Team 和 Runs 控制面

**目标:** 把 Agents / Build Teams / Skills / Runtimes 从展示页变成能操作的 agent team control plane。

**推进的 spine 段落:**

```text
Route Decision -> Team Capability -> Assignment -> Runtime Claim
```

**主要文件:**

- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/team/TeamPage.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/team/AgentsPanel.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/team/BuildTeamsPanel.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/team/SkillsPanel.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/runs/RunsPage.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/runs/RuntimesPanel.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/runs/AssignmentsPanel.tsx`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/workbench_agents.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/workbench_runtimes.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/runtime/daemon.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/runtime/capabilities.py`
- `/Users/martinlos/code/Ariadne/tests/test_workbench_agents_runtimes.py`

**实施步骤:**

- [ ] Team 页面展示真实 agent roles：Codex、Claude Code、Reviewer、Knowledge Agent、Repo Understanding Agent、Issue Factory Agent、Build Lead、Handoff Agent、Memory Agent。
- [ ] 每个 agent 显示：role、backend、capability、active assignment、blocked count、runtime compatibility。
- [ ] 支持安全配置：enabled/disabled、backend preference、model/provider name、reasoning level。
- [ ] Build Teams 定义 reusable routing presets：
  - [ ] Codex Builder + Reviewer
  - [ ] Claude Builder + Reviewer
  - [ ] Knowledge + Repo + Issue Factory
  - [ ] Human Review Required
- [ ] Skills 显示 BuildSkill packs、linked agents、allowed paths、handoff references。
- [ ] Runs 页面展示 daemon state、runtime capability、active assignment、queue、heartbeat、last error。
- [ ] Runs 页面支持 start daemon、stop daemon、refresh capability、claim next assignment。
- [ ] Codex / Claude capability probe 必须记录 evidence：command availability、login/gate status、template status。

**浏览器验收:**

- [ ] 用户能看出哪些 agent 能跑、为什么不能跑。
- [ ] 用户能从 Issue Detail assign 当前 issue 到 agent。
- [ ] 用户能在 Runs 看到 daemon 是否 claim 了这个 assignment。
- [ ] Runtime 状态不能自相矛盾，例如同时显示已授权又显示门禁关闭而无解释。

**命令:**

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m pytest tests/test_workbench_agents_runtimes.py tests/test_backend_doctor.py
ruff check .
cd /Users/martinlos/code/Ariadne/frontend/ariadne-workbench
npm run build
```

---

## Phase 5：Sources 和 Plan Changes

**目标:** Ariadne 的差异化不是多几个 agent 名字，而是外部输入和反馈能改变当前版本 issue set。

**推进的 spine 段落:**

```text
Sources -> Typed Source Artifacts -> Issue Delta -> Confirmed Current Issue Set
```

**主要文件:**

- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/sources/SourcesPage.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/plan-changes/PlanChangesPage.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/features/project-inputs/*`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/source_ingestion.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/source_analysis.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/issue_factory.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/domain/source_artifacts.py`
- `/Users/martinlos/code/Ariadne/tests/test_source_to_issue_compiler.py`
- `/Users/martinlos/code/Ariadne/tests/test_issue_factory_http.py`

**实施步骤:**

- [ ] Sources 页面第一交互改成“粘贴链接或选择本地路径”，标题/类型/摘要只是可选 override。
- [ ] 输入 GitHub repo 时生成 `RepositoryUnderstandingArtifact`，不能只读 README。
- [ ] 输入 URL/blog/paper/markdown 时生成 `KnowledgeArtifact`。
- [ ] 扫描当前目标项目时生成 `CodebaseStateArtifact`。
- [ ] 保存 source 后立即进入 visible lifecycle：queued、analyzing、analyzed、failed。
- [ ] Source artifact 页面显示：
  - [ ] source type
  - [ ] fetch / clone / scan status
  - [ ] inspected files / content
  - [ ] evidence snippets
  - [ ] relation to project goal
  - [ ] artifact path
  - [ ] failure reason
- [ ] Plan Changes 页面展示 issue delta，不展示“生成器表单”心智。
- [ ] Delta item 必须显示：
  - [ ] 新增 / 更新 / 降级 / 延后 / 拒绝
  - [ ] 为什么
  - [ ] 引用哪些 source artifacts
  - [ ] 影响哪个目标版本能力
  - [ ] acceptance criteria
- [ ] 应用 delta 后，Issues board 立即出现或更新当前版本 issue set。
- [ ] stale preview 不能 500；必须展示 refresh / compare / discard。

**浏览器验收:**

- [ ] 粘贴 `https://github.com/SWE-agent/mini-swe-agent` 后能看到 repo understanding，包含 inspected file list。
- [ ] 粘贴 `https://minimal-agent.com/` 后能看到 knowledge evidence。
- [ ] 用户能从 Sources 直接进入 Plan Changes。
- [ ] 应用 Plan Changes 后，`#issues` 看到目标项目 issue，而不是 Ariadne 自身 roadmap issue。

**命令:**

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m pytest tests/test_source_to_issue_compiler.py tests/test_issue_factory_http.py
ruff check .
cd /Users/martinlos/code/Ariadne/frontend/ariadne-workbench
npm run build
```

---

## Phase 6：Execution Evidence、Inbox、Lifecycle 硬化

**目标:** Workbench 必须像真实 agent operations 产品：assignment 被 claim，progress 可见，blocked 可恢复，结果回流 issue。

**推进的 spine 段落:**

```text
Assignment -> Codex/Claude Run -> Evidence -> Review -> Memory -> Blocker/Repair/Next Issue
```

**主要文件:**

- `/Users/martinlos/code/Ariadne/ariadne_ltb/runtime/daemon.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/runtime/assignment_runner.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/runtime/backends.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/assignment_service.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/inbox_service.py`
- `/Users/martinlos/code/Ariadne/ariadne_ltb/application/progress_events.py`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/inbox/InboxPage.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/runs/RunsPage.tsx`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/widgets/issue-detail/IssueExecution.tsx`
- `/Users/martinlos/code/Ariadne/tests/test_assignment_lifecycle.py`
- `/Users/martinlos/code/Ariadne/tests/test_inbox_actions_http.py`
- `/Users/martinlos/code/Ariadne/tests/test_execution_evidence_flow.py`

**实施步骤:**

- [ ] Assignment lifecycle 固定为：queued、claimed、running、review、blocked、failed、done。
- [ ] 增加 heartbeat、stale assignment recovery、orphan assignment detection。
- [ ] 增加 typed failure reasons：
  - [ ] `missing_runtime_capability`
  - [ ] `missing_external_execution_gate`
  - [ ] `target_repo_invalid`
  - [ ] `dirty_worktree_blocked`
  - [ ] `command_unavailable`
  - [ ] `execution_failed`
  - [ ] `tests_failed`
  - [ ] `review_failed`
  - [ ] `stale_issue_delta`
- [ ] 每个 assignment 写 progress events。
- [ ] Codex / Claude backend result 必须写：
  - [ ] handoff path
  - [ ] command template
  - [ ] backend invocation id
  - [ ] stdout / stderr
  - [ ] exit code
  - [ ] changed files
  - [ ] git diff
  - [ ] test command / result / log path
  - [ ] review artifact
  - [ ] memory artifact
  - [ ] next issue artifact
- [ ] Inbox actions 必须真实：
  - [ ] create repair issue
  - [ ] rerun assignment
  - [ ] acknowledge blocker
  - [ ] assign to human
  - [ ] link blocker to issue detail
- [ ] 解决 daemon 抢跑旧 assignment：从 Issue Detail 触发的 run-now 必须绑定当前 issue，并具有明确优先级。
- [ ] 至少人工制造两个 blocked 场景并验收：
  - [ ] `command_unavailable`
  - [ ] `missing_external_execution_gate`
  - [ ] `dirty_worktree_blocked`
  - [ ] `target_repo_invalid`
- [ ] 同一个 blocker id 必须能在 Issue Detail、Inbox、dogfood result 中追踪。

**浏览器验收:**

- [ ] 用户能看到 daemon 当前正在跑哪个 issue。
- [ ] 点击 run-now 后，当前 issue 的 progress events 更新。
- [ ] 成功或失败都能在 Issue Detail 看到 stdout/stderr、exit code、diff/tests/review。
- [ ] 失败时 Inbox 出现对应 blocker，并能创建 repair issue 或 rerun。

**命令:**

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m pytest \
  tests/test_assignment_lifecycle.py \
  tests/test_inbox_actions_http.py \
  tests/test_execution_evidence_flow.py \
  tests/test_workbench_daemon_feedback.py
ruff check .
```

---

## Phase 7：浏览器 Dogfood 闭环

**目标:** 只用浏览器证明 Ariadne 的真实产品闭环。CLI 只能用于启动服务和查看日志，不能替代用户路径。

**推进的 spine 段落:**

```text
完整 spine：Project Goal -> Sources -> Issue Delta -> Agent Run -> Evidence -> Version Progress
```

**主要文件:**

- `/Users/martinlos/code/Ariadne/docs/dogfood/2026-06-18-mini-code-agent-web-dogfood.md`
- `/Users/martinlos/code/Ariadne/docs/dogfood/2026-06-22-multica-grade-workbench-dogfood-result.md`
- `/Users/martinlos/code/Ariadne/docs/development_report.md`
- `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/e2e/multica-grade-workbench.spec.ts`
- `/Users/martinlos/code/Ariadne/scripts/verify_product_closure.sh`

**Dogfood 输入:**

- `https://minimal-agent.com/`
- `https://github.com/SWE-agent/mini-swe-agent`
- `https://github.com/e10nMa2k/cc-mini`

**浏览器用户路径:**

```text
打开 Workbench
  -> Projects: 创建或选择 mini-code-agent 目标项目
  -> Sources: 粘贴三个外部输入
  -> Sources: 等待并检查 typed artifacts
  -> Plan Changes: 生成当前版本 issue delta
  -> Plan Changes: 应用 issue delta
  -> Issues: 检查 MCA 当前版本主线 issues
  -> Issue Detail: 分配第一个实现 issue 给 Codex 或 Claude
  -> Runs: 启动或连接 daemon
  -> Issue Detail: 观察 progress / evidence
  -> 目标 repo: 验证代码被修改
  -> Issue Detail: 验证 diff / tests / review / memory / next issue
  -> Current Version Context: 版本进度更新
```

**实施步骤:**

- [ ] 增加 Playwright 或等价浏览器验收脚本。
- [ ] `scripts/verify_product_closure.sh` 检查：
  - [ ] dogfood result 文档字段完整
  - [ ] source artifacts 文件存在
  - [ ] issue delta artifact 文件存在
  - [ ] route decision / handoff artifact 文件存在
  - [ ] assignment / run evidence 文件存在
  - [ ] target repo diff/test evidence 存在
  - [ ] Workbench 状态和 artifact 状态一致
- [ ] Dogfood target project 不能和 Ariadne repo 混淆。
- [ ] 生成的 issue 必须是目标项目 issue，不是 Ariadne 内部 roadmap issue。
- [ ] Codex / Claude 只有在本地 gate 和 credential 满足时执行。
- [ ] 如果 Codex / Claude 不能运行，dogfood 结果必须记录 exact blocker，并在 Workbench 可恢复。
- [ ] 更新 development report，不能声称未发生的真实执行。

**闭环成功标准:**

- [ ] 用户全程通过浏览器完成路径。
- [ ] target project 出现可运行 v0.1 产物。
- [ ] Issue Detail 有 run evidence。
- [ ] Runs 有 daemon / assignment evidence。
- [ ] Inbox 没有未处理 critical blocker；如果有，必须说明为什么不是产品闭环成功。
- [ ] Current Version Context 展示版本进度。
- [ ] dogfood result 文档记录截图、artifact path、commit hash、blocked/success 状态。

**允许的失败完成状态:**

如果真实 Codex / Claude 执行被环境阻塞，可以结束为 `blocked but product-visible`，但必须满足：

- [ ] blocker 在 Issue Detail 可见。
- [ ] blocker 在 Inbox 可见。
- [ ] blocker 有 typed failure reason。
- [ ] blocker 有 repair / rerun / human action。
- [ ] dogfood result 记录 exact blocker。
- [ ] 不声称 Ariadne 已完成真实执行闭环。

**命令:**

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m pytest
ruff check .
python3.11 -m ariadne_ltb.cli doctor product
cd /Users/martinlos/code/Ariadne/frontend/ariadne-workbench
npm run build
npm run e2e
```

---

## 分支、提交、PR、回滚规则

- [ ] 每个 Phase 至少一个独立 commit。
- [ ] 大 Phase 可以拆分 PR，但每个 PR 必须有浏览器 evidence。
- [ ] 不允许合并只通过 `npm run build` 但未通过浏览器验收的阶段。
- [ ] 涉及 API / schema / UI 路由的 Phase 必须写 rollback 方式。
- [ ] 如果 worktree 有用户未跟踪改动，不要覆盖；只 stage 本任务相关文件。
- [ ] 每阶段报告必须写：
  - [ ] commit hash
  - [ ] changed files
  - [ ] tests
  - [ ] browser evidence
  - [ ] artifact paths
  - [ ] known blockers
  - [ ] rollback path

推荐提交顺序：

```text
Phase 1: product IA and current version context
Phase 2: multica-style API projections
Phase 3: issues workbench
Phase 4: team and runs control surfaces
Phase 5: source-to-plan-changes integration
Phase 6: lifecycle, inbox, execution evidence
Phase 7: browser dogfood closure evidence
```

---

## 最终验收门槛

最终不能用“模块都做了”来验收。只能用这条链路验收：

```text
浏览器创建/选择项目
  -> 浏览器添加外部输入
  -> 浏览器看到 typed artifacts
  -> 浏览器生成并应用 issue delta
  -> 浏览器看到当前版本 issue set
  -> 浏览器分配 issue 给 Codex/Claude
  -> daemon claim assignment
  -> Codex/Claude 改目标项目代码，或给出可恢复 blocker
  -> Workbench 回流 diff/tests/review/memory/next issue
  -> Current Version Context 更新
```

如果没有完成这条链路，就不能说 Ariadne 达到 Multica 级成熟度。

如果完成的是 blocked 路径，也要诚实写成：

```text
产品可见的 blocked 闭环已完成；
真实 Codex/Claude 成功执行未完成；
阻塞原因是 <exact reason>。
```

---

## 本次 subagent 评审吸收情况

产品心智评审已吸收：

- [x] `Issues` 是默认操作面，但必须 scoped 到 current project/version。
- [x] `Delivery` 改为 `Current Version Context`，不再作为普通报告页。
- [x] 一级导航从 11 个入口压缩到 7 个入口。
- [x] `Issue Factory` 面向用户改为 `Plan Changes`，内部仍可保留 implementation name。
- [x] Primary Builder Journey 上移为全计划 spine。

架构边界评审已吸收：

- [x] `Issue == BuildTicket projection` 写入边界契约。
- [x] 禁止新增 parallel issue store。
- [x] 增加 API 迁移矩阵。
- [x] `App.tsx` 重构拆成 route alias -> shell extraction -> page extraction -> legacy cleanup。
- [x] Inbox read model 和 runtime truth model 前移到 Phase 2。

执行验收评审已吸收：

- [x] 全文改中文。
- [x] 增加计划时间戳。
- [x] 增加每阶段统一出门门槛。
- [x] 增加非 fixture local API smoke。
- [x] 增加真实 runtime evidence 要求。
- [x] 增加 blocked dogfood 验收。
- [x] 增加 `npm run e2e` / `verify_product_closure.sh` 硬门槛。
- [x] 增加 commit / PR / rollback 规则。
