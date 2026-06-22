# CC Review Prompt — Ariadne Phase 1-3 Workbench Merge Review

你现在 review Ariadne `main` 分支，当前最新提交应包含：

```text
31d591a Merge Phase 1-3 Workbench rebuild
```

目标不是继续实现新功能，而是严格 review Phase 1-3 是否真的把 Ariadne Workbench 从 demo-like ticket list 推进到 Multica-style 的当前版本 issue workbench。

## 必读上下文

先读：

```text
AGENTS.md
README.md
docs/adr/ADR-0004-ticket-centered-agent-workbench.md
docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md
docs/superpowers/plans/2026-06-22-multica-grade-workbench-execution-brief.md
docs/superpowers/plans/2026-06-22-multica-grade-agent-team-workbench-rebuild-plan.md
docs/superpowers/plans/2026-06-22-phase2-handoff.md
docs/superpowers/plans/2026-06-22-phase3-handoff.md
```

重点代码：

```text
ariadne_ltb/interfaces/http/routes.py
ariadne_ltb/application/workbench_issues.py
ariadne_ltb/application/workbench_issue_detail.py
ariadne_ltb/application/workbench_agents.py
ariadne_ltb/application/workbench_runtimes.py
ariadne_ltb/application/workbench_projects.py
ariadne_ltb/application/workbench_inbox.py
ariadne_ltb/application/workbench_task_snapshot.py
ariadne_ltb/application/dtos.py
frontend/ariadne-workbench/src/App.tsx
frontend/ariadne-workbench/src/app/routes.ts
frontend/ariadne-workbench/src/app/shell/Sidebar.tsx
frontend/ariadne-workbench/src/widgets/current-version/CurrentVersionStrip.tsx
frontend/ariadne-workbench/src/pages/issues/IssuesPage.tsx
frontend/ariadne-workbench/src/pages/issues/IssueBoard.tsx
frontend/ariadne-workbench/src/pages/issues/IssueCard.tsx
frontend/ariadne-workbench/src/pages/issues/IssueDetail.tsx
frontend/ariadne-workbench/src/shared/api/client.ts
frontend/ariadne-workbench/src/shared/api/types.ts
tests/test_multica_grade_workbench_api.py
tests/test_frontend_api_contract_static.py
```

Evidence：

```text
docs/evidence/phase1-current-version-context/
docs/evidence/phase2-api-projections/
docs/evidence/phase3-issues-workbench/browser-validation.json
docs/evidence/phase3-issues-workbench/*.png
```

## Review 目标

请从最严苛工程 reviewer 角度判断：

1. Phase 1 是否真的把默认入口从 Delivery 状态页改成 Issues / current version context。
2. Phase 2 是否真的提供了按页面组织的 read-model API，而不是继续让前端依赖巨型 `/api/workbench`。
3. Phase 3 是否真的让 `#issues` 使用 `GET /api/issues`，并让 `#issues/{key}` 使用 `GET /api/issues/{key}`。
4. Issue detail 的 assign/comment/run-now/rerun 是否调用真实 API，不是 mock / fixture / local-only fake success。
5. `/api/issues` 是否仍然是 BuildTicket projection，没有引入独立 Issue persistence。
6. `#issues` 是否只展示 current project/version mainline，不退回展示所有历史 tickets。
7. `CurrentVersionStrip` 是否始终可见，并且没有破坏 Project Version Delivery 语义。
8. Legacy routes `#sources`, `#plan-changes`, `#diagnostics`, `#delivery` 是否还工作。
9. 是否存在 demo-first / fake-first / dry-run-first 文案或 UI 误导。
10. 是否有架构漂移：Goal-first runtime、React Router、新存储、新后端依赖、Go/Postgres/auth/workspace/billing 等。

## 必跑验证

请在本地运行：

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m pytest
ruff check .
cd frontend/ariadne-workbench && npm run build
```

如果启动浏览器验收：

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8766
```

然后确认：

```text
http://127.0.0.1:8766/#issues
http://127.0.0.1:8766/#issues/MCA-002
http://127.0.0.1:8766/#sources
http://127.0.0.1:8766/#plan-changes
http://127.0.0.1:8766/#diagnostics
http://127.0.0.1:8766/#delivery  -> should redirect to #issues
```

## 输出格式

请不要泛泛总结。请按这个格式输出：

```markdown
# Ariadne Phase 1-3 Review

## Verdict
pass / pass-with-issues / fail

## Blocking Issues
- [P0/P1] file:line — exact issue, why it blocks, how to fix

## Non-blocking Issues
- [P2/P3] file:line — exact issue, recommended fix

## Product-chain Assessment
- current-version context:
- issue board:
- issue detail:
- real API actions:
- evidence visibility:
- Multica-style alignment:

## Architecture Drift Check
- BuildTicket-centered:
- no separate Issue persistence:
- local-first:
- no fake acceptance:
- no new backend dependencies:

## Verification Run
- pytest:
- ruff:
- frontend build:
- browser smoke:

## Recommended Next Phase
写清楚 Phase 4 应该优先做什么，以及为什么。
```

## 审查边界

不要实现代码，先 review。
不要因为有截图 evidence 就默认通过；截图只证明路径曾经跑通，不证明架构没有问题。
不要要求把 Ariadne 变成 Multica clone；Ariadne 当前边界是 local-first、single-user、Python runtime、JSON/.ariadne 存储。
