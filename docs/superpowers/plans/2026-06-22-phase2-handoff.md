# Phase 2 Handoff: Multica-style API Projections

> **For Codex:** 先读 `AGENTS.md`（它会被更新为 Phase 2），再读本文档。

## 背景

Phase 1 已完成并合并（PR #24）。前端现在默认落在 `#issues`，顶部有 `CurrentVersionContext` strip。但前端仍然从巨型 `GET /api/workbench` 一个 endpoint 拿所有数据。

Phase 2 的目标：**新增按页面组织的 read-model endpoints，让前端每个页面可以按需请求数据，但所有数据仍然投影自现有 store，不新增第二套模型。**

## 核心约束

1. **所有新 endpoint 都是 projection（只读投影）：** 从现有 `AriadneStore` 里的 `BuildTicket`、`TicketAssignment`、`AgentRun`、`InboxItem`、`SourceDocument` 等投影出来。不新增模型文件、不新增 JSON 存储。
2. **`/api/workbench` 保留：** 不删除、不修改。新 endpoint 是平行扩展，不是替代。前端在 Phase 3 才切换到新 API。
3. **Issue = BuildTicket 投影：** `/api/issues` 返回的每条 issue 背后必须是一个 `BuildTicket`。不允许存在不对应 BuildTicket 的 issue。
4. **Scoped to current version mainline：** `GET /api/issues` 默认只返回当前 project/version mainline issue set。不返回所有历史 tickets。

## 现有代码模式（必须遵循）

### 路由模式

```python
# ariadne_ltb/interfaces/http/routes.py
@router.get("/api/issues")
def list_issues(store: AriadneStore = Depends(get_store)) -> dict:
    return WorkbenchIssuesService(store).list().model_dump(mode="json")
```

- FastAPI router，`Depends(get_store)` 注入 store
- 路由层只做一行调用 + `.model_dump(mode="json")`
- 业务逻辑在 `ariadne_ltb/application/workbench_*.py`

### Service 模式

```python
# ariadne_ltb/application/workbench_issues.py
class WorkbenchIssuesService:
    def __init__(self, store: AriadneStore) -> None:
        self._store = store

    def list(self) -> IssueListResponse:
        tickets = self._store.list_tickets()
        # filter to current version mainline
        # map to IssueListItemDTO
        ...
```

### DTO 模式

```python
# ariadne_ltb/application/dtos.py
class IssueListItemDTO(AriadneDTO):
    id: str
    key: str
    title: str
    status: str
    ...
```

- 所有 DTO 继承 `AriadneDTO`（基类是 `BaseModel`）
- 放在 `ariadne_ltb/application/dtos.py`

### Mapper 模式

已有 `ticket_summary()`、`inbox_item_dto()`、`assignment_dto()` 等。新 projection 如果字段覆盖范围不同，新建 mapper 函数放 `mappers.py`。如果完全复用现有 mapper，直接用。

## 新增文件

| 文件 | 职责 |
|---|---|
| `ariadne_ltb/application/workbench_issues.py` | `/api/issues` list + detail + actions |
| `ariadne_ltb/application/workbench_inbox.py` | `/api/inbox` list |
| `ariadne_ltb/application/workbench_agents.py` | `/api/team/agents` + `/api/team/build-teams` + `/api/team/skills` |
| `ariadne_ltb/application/workbench_runtimes.py` | `/api/runs/runtimes` + `/api/runs/assignments` |
| `ariadne_ltb/application/workbench_projects.py` | `/api/projects` list + detail |
| `ariadne_ltb/application/workbench_task_snapshot.py` | `/api/agent-task-snapshot` |
| `tests/test_multica_grade_workbench_api.py` | 新 API 的集成测试 |

## 新增 Endpoints（完整列表）

```
GET    /api/issues                        → IssueListResponse (scoped to current version)
GET    /api/issues/{issue_id_or_key}      → IssueDetailResponse
PATCH  /api/issues/{issue_id_or_key}      → IssueDetailResponse (update title/status/priority)
POST   /api/issues/{issue_id_or_key}/comments  → CommentResponse
GET    /api/issues/{issue_id_or_key}/timeline  → TimelineResponse
POST   /api/issues/{issue_id_or_key}/assign    → AssignmentResponse (delegates to existing AssignTicketService)
POST   /api/issues/{issue_id_or_key}/rerun     → AssignmentResponse (delegates to existing RunAssignmentService)
POST   /api/issues/{issue_id_or_key}/run-now   → AssignmentResponse (delegates to existing DaemonControlService)
GET    /api/inbox                         → InboxListResponse
GET    /api/agent-task-snapshot           → AgentTaskSnapshotResponse
GET    /api/projects                      → ProjectListResponse
GET    /api/projects/{project_id}         → ProjectDetailResponse
GET    /api/team/agents                   → AgentListResponse
GET    /api/team/build-teams              → BuildTeamListResponse
GET    /api/team/skills                   → SkillListResponse
GET    /api/runs/runtimes                 → RuntimeListResponse
GET    /api/runs/assignments              → AssignmentListResponse
```

## Projection 字段规范

### IssueListItemDTO

```python
class IssueListItemDTO(AriadneDTO):
    id: str                    # ticket.id
    key: str                   # ticket.key
    title: str                 # ticket.title
    status: str                # ticket.status.value
    priority: str              # ticket.priority or "medium"
    assignee: str | None       # latest assignment agent_name
    project: str | None        # ticket.project_id
    target_version: str | None # from current delivery context
    source_count: int          # len(ticket.source_ids or [])
    evidence_count: int        # count of execution results
    last_run_status: str | None  # latest AgentRun status
    review_verdict: str | None   # latest review verdict
    blocked_reason: str | None   # first blocker if blocked
    updated_at: str            # ticket.updated_at or created_at
```

### IssueDetailDTO

在 IssueListItemDTO 基础上增加：

```python
class IssueDetailDTO(AriadneDTO):
    # ... all IssueListItemDTO fields ...
    body: str                  # ticket.description
    comments: list[CommentDTO]
    timeline: list[TimelineEventDTO]
    assignments: list[AssignmentDTO]
    execution_results: list[ExecutionResultSummaryDTO]
    source_links: list[str]
    route_decision: dict | None
    handoff: dict | None
    diff_summary: str | None
    test_summary: str | None
    review_summary: str | None
    next_issue_links: list[str]
```

### InboxListItemDTO

```python
class InboxListItemDTO(AriadneDTO):
    id: str
    issue_key: str | None      # linked ticket key
    failure_reason: str
    severity: str              # InboxSeverity value
    action_type: str           # repair / rerun / acknowledge / resolve
    created_at: str
    status: str                # InboxStatus value
    resolution_note: str | None
```

### AgentTaskSnapshotDTO

```python
class AgentTaskSnapshotDTO(AriadneDTO):
    active_assignment: str | None  # assignment_id if running
    current_issue_key: str | None
    backend: str | None
    queued_count: int
    blocked_count: int
    heartbeat: str | None      # last heartbeat timestamp
    last_event: str | None     # last event summary
```

## Issue Scoping 逻辑

`GET /api/issues` 必须实现以下 scoping：

```python
def _current_version_mainline_tickets(self) -> list[BuildTicket]:
    delivery = self._store.current_version_delivery()  # or equivalent
    if delivery and delivery.delivery_items:
        mainline_keys = {item.ticket_key for item in delivery.delivery_items}
        return [t for t in self._store.list_tickets() if t.key in mainline_keys]
    # fallback: return all non-archived tickets
    return [t for t in self._store.list_tickets() if t.status != TicketStatus.ARCHIVED]
```

这跟 Phase 1 前端 `getCurrentVersionTickets()` 的逻辑一致。

## Action endpoints 必须复用现有 service

不要重新实现 assign/run/comment 逻辑。直接调用：

| Endpoint | 调用 |
|---|---|
| `POST /api/issues/{id}/assign` | `AssignTicketService(store).assign(id, payload)` |
| `POST /api/issues/{id}/rerun` | `RunAssignmentService(store).run(assignment_id, payload)` |
| `POST /api/issues/{id}/run-now` | `DaemonControlService(store).run_now(assignment_id, payload)` |
| `POST /api/issues/{id}/comments` | `CommentService(store).add_human_comment(id, payload)` |
| `GET /api/issues/{id}/timeline` | `CommentService(store).timeline(id)` |

对于 `rerun` 和 `run-now`：需要先从 ticket 找到最新 assignment_id，然后调用现有 service。

## 不做（硬边界）

- 不修改前端代码（Phase 3 才让前端切换到新 API）
- 不修改 `GET /api/workbench` 的返回结构
- 不新增 model 类到 `models.py`
- 不新增 JSON/JSONL 文件存储
- 不实现 write 操作超出 PATCH title/status/priority + assign + rerun + run-now + comments
- 不实现 issue board view / kanban（那是前端 Phase 3 的事）
- 不实现 daemon claim / heartbeat / retry / orphan recovery（Phase 6）
- 不实现 WebSocket subscription 给新 endpoints
- 不修改现有测试的断言（可以新增测试文件）
- 不引入新 Python 依赖

## 验收标准

### 1. 测试通过

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m pytest
ruff check .
cd frontend/ariadne-workbench && npm run build
```

全部通过。新增测试文件 `tests/test_multica_grade_workbench_api.py` 中至少覆盖：
- `GET /api/issues` 返回当前版本 mainline tickets
- `GET /api/issues/{key}` 返回 detail
- `GET /api/inbox` 返回 active inbox items
- `GET /api/runs/runtimes` 返回 runtime 状态
- `GET /api/team/agents` 返回 agent profiles
- `GET /api/projects` 返回 target projects

### 2. 真实 API Smoke

启动 workbench 后（`python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8766`），用 curl 验证：

```bash
curl -s http://127.0.0.1:8766/api/issues | python3.11 -m json.tool
curl -s http://127.0.0.1:8766/api/inbox | python3.11 -m json.tool
curl -s http://127.0.0.1:8766/api/runs/runtimes | python3.11 -m json.tool
curl -s http://127.0.0.1:8766/api/team/agents | python3.11 -m json.tool
curl -s http://127.0.0.1:8766/api/projects | python3.11 -m json.tool
curl -s http://127.0.0.1:8766/api/agent-task-snapshot | python3.11 -m json.tool
```

每个 response 必须：
- HTTP 200
- 合法 JSON
- 不包含 mock/fixture/demo 标记
- `issues` 列表只包含当前版本 mainline（不是全部历史 tickets）

### 3. 保存 evidence

把 curl 响应样例保存到 `docs/evidence/phase2-api-projections/` 目录。

### 4. 旧 API 不受影响

```bash
curl -s http://127.0.0.1:8766/api/workbench | python3.11 -m json.tool | head -30
```

格式与 Phase 1 之前完全一致。

## 启动命令

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8766
```

注意：`python3.11 -m ariadne_ltb.interfaces.http.server` 不存在。只能用 CLI 入口启动。

## 分支和 PR

- Branch: `codex/phase2-api-projections`
- PR title: `Phase 2: Multica-style API projections`
- PR base: `main`（确保 Phase 1 已合并到 main）
