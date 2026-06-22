# Phase 3 Handoff: Issues Workbench 重构

> **For Codex:** 先读 `AGENTS.md`（会被更新为 Phase 3），再读本文档。

## 背景

Phase 1 建立了导航骨架和 CurrentVersionContext strip。Phase 2 新增了 17 个 read-model API endpoint。但前端仍然从巨型 `GET /api/workbench` 拿数据，issue 页面仍然是简单的 ticket 列表。

Phase 3 的目标：**把 Ariadne 的主工作面从 ticket 列表改造为 issue board + issue detail，前端切换到 Phase 2 的新 API。**

## 核心约束

1. **不改后端 Python 代码。** Phase 2 已提供所有需要的 API。如果发现 API 返回字段不足，报 blocker，不要自行修改后端。
2. **Issue = BuildTicket 投影（UI 层）：** board 上每个 issue 背后是 BuildTicket。UI 不做自己的 issue 缓存或 local state 持久化。
3. **Scoped to current version mainline：** `#issues` 默认只展示 `GET /api/issues` 返回的当前版本 mainline set。不展示所有历史。
4. **所有 action 必须调用真实 API：** assign、rerun、run-now、comment 不能假装成功。
5. **CurrentVersionContext strip 保持不变** — 它已经从 `/api/workbench` 拿数据且工作正常。Phase 3 不动它。

## 实施策略

分四步，按顺序执行：

### Step 1: Shell extraction

从 App.tsx 抽离出结构：

```
src/
  App.tsx              → 只做 shell（sidebar + router + context strip）
  app/
    shell/
      Sidebar.tsx      → 从 App.tsx 抽出 Sidebar 函数
    routes.ts          → hash route 逻辑
  pages/
    issues/
      IssuesPage.tsx   → list + board view
      IssueDetail.tsx  → detail page
    sources/           → 现有 sources page 抽出
    plan-changes/      → 现有 tasks page 抽出
    diagnostics/       → 现有 diagnostics 抽出
  shared/
    api/
      client.ts        → 保持
      types.ts         → 保持
  widgets/
    current-version/
      CurrentVersionStrip.tsx → 从 App.tsx 抽出 CurrentVersionContext
```

注意：
- 不引入 React Router。继续用现有 hash-based routing + `useState<PageKey>`
- 只是把函数从一个文件搬到多个文件，不改逻辑
- 搬完后 `npm run build` 必须成功，行为不变

### Step 2: Issues page 切换到新 API

`IssuesPage.tsx` 从 `GET /api/issues` 获取数据，不再从 workbench aggregate 解析。

```typescript
// pages/issues/IssuesPage.tsx
async function fetchIssues(): Promise<IssueListItem[]> {
  const response = await fetch('/api/issues');
  const data = await response.json();
  return data.issues;
}
```

Issues 页面展示方式改为 Board view：

**Board columns:** Backlog → Ready → Assigned → Running → Review → Blocked → Done

列映射（从 issue.status）：
- `open` / `planning` → Backlog
- `ready` → Ready
- `assigned` → Assigned
- `running` / `in_progress` → Running
- `reviewing` / `review_pending` → Review
- `blocked` → Blocked
- `done` / `closed` / `released` → Done

**Issue card 展示：**
- key (e.g. ARI-003)
- title
- priority badge
- assignee / backend name
- run state indicator
- review verdict indicator
- evidence count
- blocked marker (if blocked)

### Step 3: Issue detail page

Route: `#issues/{issue_key_or_id}` → 展示 `GET /api/issues/{key}` 返回的完整数据。

**Issue detail layout:**

```
┌─────────────────────────────────────────────────────┐
│ Header: key + title + status badge + priority       │
│ Actions: Assign / Run Now / Rerun / Add Comment     │
├───────────────────────────────┬─────────────────────┤
│ Main content (left 2/3)       │ Sidebar (right 1/3) │
│                               │                     │
│ - Issue body/description      │ - Assignee          │
│ - Source evidence links       │ - Backend           │
│ - Route decision              │ - Run state         │
│ - Execution results           │ - Review verdict    │
│ - Diff / tests summary        │ - Evidence count    │
│ - Timeline / activity         │ - Blocked reason    │
│ - Comments                    │ - Next issue links  │
│                               │ - Handoff packet    │
└───────────────────────────────┴─────────────────────┘
```

**Primary actions 必须调用真实 API：**

| Action | API call |
|---|---|
| Assign | `POST /api/issues/{key}/assign` |
| Run Now | `POST /api/issues/{key}/run-now` |
| Rerun | `POST /api/issues/{key}/rerun` |
| Add Comment | `POST /api/issues/{key}/comments` |

如果 API 返回错误，展示错误信息（不假装成功）。

### Step 4: Legacy cleanup

- 从 App.tsx 删除已搬走的内联组件
- 删除现有 `"ready"` page 的旧 issue list 渲染逻辑（已被 IssuesPage board 替代）
- 保留 `/api/workbench` 调用给 CurrentVersionContext strip 使用
- 确保所有旧 hash route（`#ready`, `#issues`, `#issues/ARI-003`）仍然正常工作

## 不做（硬边界）

- 不改后端 Python 代码
- 不新增 API endpoint
- 不引入 React Router（继续 hash + useState）
- 不引入新 npm 依赖（除非是 lucide-react 中已有的 icon）
- 不实现 drag-drop（board 只是展示分列，不支持拖拽换状态）
- 不实现 issue 创建/删除（只有 patch title/status/priority）
- 不实现 WebSocket 实时更新
- 不修改 CurrentVersionContext strip 的数据来源
- 不实现 Team/Runs/Inbox 页面改造（Phase 4）

## 新文件结构

```
frontend/ariadne-workbench/src/
├── App.tsx                          (shell: sidebar + router + main wrapper)
├── app/
│   ├── shell/
│   │   └── Sidebar.tsx
│   └── routes.ts                    (parseHashRoute, pageHash, etc.)
├── pages/
│   ├── issues/
│   │   ├── IssuesPage.tsx           (board view, fetches /api/issues)
│   │   ├── IssueBoard.tsx           (columns layout)
│   │   ├── IssueCard.tsx            (single card in board)
│   │   └── IssueDetail.tsx          (detail page, fetches /api/issues/{key})
│   ├── sources/
│   │   └── SourcesPage.tsx          (extracted from App.tsx KnowledgePage)
│   ├── plan-changes/
│   │   └── PlanChangesPage.tsx      (extracted from App.tsx TasksPage)
│   └── diagnostics/
│       └── DiagnosticsPage.tsx      (extracted from App.tsx diagnostics section)
├── widgets/
│   └── current-version/
│       └── CurrentVersionStrip.tsx  (extracted from App.tsx CurrentVersionContext)
├── shared/
│   └── api/
│       ├── client.ts                (existing, add new fetch helpers)
│       └── types.ts                 (existing, add issue list/detail types)
├── data.ts                          (existing, keep for workbench aggregate)
├── types.ts                         (existing, keep)
├── styles.css                       (existing, extend)
└── main.tsx                         (existing, unchanged)
```

## Type 定义（新增到 shared/api/types.ts）

```typescript
interface IssueListItem {
  id: string;
  key: string;
  title: string;
  status: string;
  priority: string;
  assignee: string | null;
  project: string | null;
  target_version: string | null;
  source_count: number;
  evidence_count: number;
  last_run_status: string | null;
  review_verdict: string | null;
  blocked_reason: string | null;
  updated_at: string;
}

interface IssueDetail extends IssueListItem {
  body: string;
  comments: Comment[];
  timeline: TimelineEvent[];
  assignments: Assignment[];
  execution_results: ExecutionResultSummary[];
  source_links: string[];
  route_decision: object | null;
  handoff: object | null;
  diff_summary: string | null;
  test_summary: string | null;
  review_summary: string | null;
  next_issue_links: string[];
}
```

## 验收标准

### 自动化

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m pytest
ruff check .
cd frontend/ariadne-workbench && npm run build
```

### 浏览器验收

启动 workbench：
```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8766
```

确认：
1. `http://127.0.0.1:8766/#issues` — 看到 issue board，columns 按 status 分组
2. 点击某个 issue card → 跳转到 `#issues/ARI-003`（或真实 key）
3. Issue detail 页面展示完整信息：body, assignee, evidence, timeline, comments
4. 点 "Add Comment" → 调用 API → comment 出现在列表
5. 点 "Assign" → 调用 API → assignment 信息更新
6. 如果 issue 没有 assignment，点 "Rerun"/"Run Now" → 展示错误信息而非假装成功
7. CurrentVersionContext strip 仍然正常显示在顶部
8. 所有旧 hash route 仍然工作（`#sources`, `#plan-changes`, `#diagnostics`）
9. 页面没有 static fixture / mock 数据

截图保存到 `docs/evidence/phase3-issues-workbench/`。

## 启动命令

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8766
```

## 分支和 PR

- Branch: `codex/phase3-issues-workbench`
- PR title: `Phase 3: Issues workbench board and detail`
- PR base: `main`（确保 Phase 1 和 Phase 2 已合并到 main）
