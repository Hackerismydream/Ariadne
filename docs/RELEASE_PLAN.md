# Ariadne v1.0 Release Plan

目标：把当前开发状态合并到 main，清理分支，准备公开发布。

## 现状快照（2026-06-24）

- 420 tests 全部通过，ruff 零 warning
- main 已合并到 Phase 6，Phase 8 的 2 个 commit 待合并
- License: Apache 2.0 ✓
- .env gitignored，git 历史无泄露 ✓
- 无 CI workflow

## Step 1: 合并 Phase 8 到 main

```bash
git checkout main
git merge codex/phase8-polish-review-fixes --no-ff -m "Merge Phase 8 knowledge orchestration and polish fixes"
```

合并后跑一遍验证：

```bash
uv run pytest -q
uv run ruff check .
```

## Step 2: 处理未跟踪文件

把 `docs/templates/CURRENT_VERSION_BRIEF.md` 加入版本控制：

```bash
git add docs/templates/CURRENT_VERSION_BRIEF.md
git commit -m "docs: add current version brief template"
```

## Step 3: 删除已合并的本地分支

Phase 1-6 全部已合并到 main，安全删除：

```bash
git branch -d codex/phase1-current-version-context
git branch -d codex/phase2-api-projections
git branch -d codex/phase3-issues-workbench
git branch -d codex/phase4-team-runs-inbox
git branch -d codex/phase5-sources-plan-changes
git branch -d codex/phase6-lifecycle-evidence
```

Phase 8 合并后也删除：

```bash
git branch -d codex/phase8-knowledge-orchestration
git branch -d codex/phase8-polish-review-fixes
```

## Step 4: 删除过时的远古分支

以下分支落后 main 150+ commits，内容已被后续 phase 覆盖，安全删除：

```bash
# 本地
git branch -D codex/ari-mul-96-merge-gate-policy-engine-isolated
git branch -D codex/ari-mul-97-conflict-detection-report
git branch -D codex/ariadne-core-backlog-mutation-1b
git branch -D codex/ariadne-core-route-cleanup
git branch -D codex/ariadne-core-runtime-maturity-2
git branch -D codex/ariadne-core-runtime-section-plan
git branch -D codex/ariadne-core-ticket-state-1a
git branch -D codex/real-source-to-agent-compiler-plan

# 远程
git push origin --delete codex/ari-mul-96-merge-gate-policy-engine-isolated
git push origin --delete codex/ari-mul-97-conflict-detection-report
git push origin --delete codex/ariadne-core-backlog-mutation-1b
git push origin --delete codex/ariadne-core-route-cleanup
git push origin --delete codex/ariadne-core-runtime-maturity-2
git push origin --delete codex/ariadne-core-runtime-section-plan
git push origin --delete codex/ariadne-core-ticket-state-1a
git push origin --delete codex/real-source-to-agent-compiler-plan
```

也删除已合并分支的远程副本：

```bash
git push origin --delete codex/phase1-current-version-context
git push origin --delete codex/phase2-api-projections
git push origin --delete codex/phase3-issues-workbench
git push origin --delete codex/phase4-team-runs-inbox
git push origin --delete codex/phase5-sources-plan-changes
git push origin --delete codex/phase6-lifecycle-evidence
git push origin --delete codex/phase8-knowledge-orchestration
git push origin --delete codex/phase8-polish-review-fixes
```

如果存在 `pr-15` 且已关闭，也删除：

```bash
git push origin --delete pr-15
```

## Step 5: 添加 GitHub Actions CI

创建 `.github/workflows/ci.yml`：

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: uv python install ${{ matrix.python-version }}
      - run: uv sync --dev
      - run: uv run ruff check .
      - run: uv run pytest -q
```

```bash
mkdir -p .github/workflows
# 写入上面的内容到 .github/workflows/ci.yml
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions test workflow"
```

## Step 6: 推送 main 并打 tag

```bash
git push origin main
git tag v1.0.0 -m "Ariadne v1.0.0 — local-first Agent Workbench"
git push origin v1.0.0
```

## Step 7: 最终验证

```bash
uv run pytest -q
uv run ruff check .
git log --oneline -10
git branch -a  # 确认只剩 main
git status     # 确认 working tree clean
```

## 不做的事

- **不发 PyPI**：这是作品集项目，GitHub repo 就够了
- **不改 README**：README 已经很完整，不需要为发布特意改写
- **不加 CHANGELOG**：git log 就是 changelog，单人项目不需要额外维护

## 执行顺序总结

1. 合并 Phase 8 → main
2. 提交未跟踪文件
3. 删除已合并本地分支
4. 删除过时本地+远程分支
5. 添加 CI workflow
6. 推送 main + 打 tag
7. 最终验证
