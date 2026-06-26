# Ariadne Project Version Delivery Closure Phase

创建时间：2026-06-26

## 一句话目标

把 Ariadne 从“很多 agent/workbench 能力模块”收敛成一条真实用户链路：

```text
用户在浏览器里创建或选择目标项目
  -> 添加外部知识
  -> Ariadne 生成当前版本 issue set
  -> 用户确认 issue delta
  -> 分配给真实 Codex / Claude agent
  -> daemon claim assignment
  -> 真实 backend 尝试执行目标项目
  -> diff / tests / review / inbox / memory / next issue 回流
  -> 当前版本进度可见
```

如果真实 Codex / Claude 因登录、quota、执行门禁或本机环境阻塞，结果必须是
`BLOCKED_WITH_EVIDENCE`。这可以是诚实结果，但不能算版本闭环成功。

## 为什么重置阶段

Multica downstream parity phase 已完成到可验证 skeleton：

```text
docs/evidence/multica-downstream-parity/closure-result.json
```

该 closure 证明 Ariadne 已经有：

- persisted AgentDefinition；
- agent detail 的 activity / tasks / skills / instructions / environment 投影；
- assignment queue；
- daemon claim；
- CodexBackend gated blocked result；
- Inbox blocker；
- memory / Feishu preview / next tickets / board evidence。

但它没有证明：

- 用户能从浏览器推进一个目标项目版本；
- 外部知识能稳定生成目标项目 issue set；
- Codex / Claude 真实修改目标 repo；
- Workbench 像 Multica 一样让用户清楚看到“谁在做哪个 issue，做到哪，怎么继续”。

因此下一阶段不再以“补更多模块”作为验收，而只接受 Project Version Delivery
闭环证据。

## 当前北极星

Ariadne 面向 AI Builder。

AI Builder 给 Ariadne 一个目标项目、目标版本和外部知识。Ariadne 负责把知识和
代码库状态编译成 issue，再组织本地 agent team 调度 Codex / Claude Code 推进
目标项目。

```text
Sources / Project Goal / Codebase
        ↓
ProjectKnowledge + Source Artifacts
        ↓
Issue Delta
        ↓
Current Version Issue Set
        ↓
Agent Assignment
        ↓
Runtime Claim
        ↓
Codex / Claude execution
        ↓
Evidence / Review / Inbox / Memory / Next Issues
        ↓
Current Version Progress
```

## 非目标

- 不继续做 CLI-first product path。
- 不用 `demo full`、`fake-codex`、static fixture、mock data 作为产品验收。
- 不新增独立 Issue persistence；Issue 仍是 BuildTicket 的产品投影。
- 不 fork Multica，不引入 Go / Postgres / auth / multi-workspace / billing。
- 不做视觉 polish 来掩盖链路没闭合。
- 不用 blocked rehearsal 冒充版本交付成功。

## 必须修正的文档口径

后续 agent 读到当前文档时，必须得到以下判断：

1. Ariadne 的产品入口是 Workbench 浏览器，不是 CLI。
2. CLI 是本地运维、调试、自动化和 fallback 入口。
3. 真正验收是浏览器 Project Version Delivery 闭环。
4. Multica 是下层 agent work-management 的产品语义 benchmark。
5. Ariadne 比 Multica 多的一层是 knowledge/source-to-issue orchestration。
6. 任何不能推动当前版本 issue set 走向真实 backend execution 的工作，都不是本阶段产品进展。

## 下一阶段实施切片

### Slice 1: Workbench-first 项目入口

目标：用户打开 Workbench 后第一眼知道“我正在推进哪个项目版本”。

必须做到：

- Project / Target Version / Goal 是页面主上下文；
- target repo 缺失时，页面给出创建/选择/注册路径，不显示裸 422；
- Sources / Plan Changes / Issues / Team / Runs / Inbox 都围绕同一个 current version；
- 历史 tickets 默认降噪，不污染当前版本。

### Slice 2: Source-to-Issue 真正面向目标项目

目标：外部输入必须产生目标项目 issue，不是 Ariadne 自己的建设任务。

必须做到：

- GitHub repo / blog / markdown / target codebase 都进入 Source Artifact；
- GitHub repo 不能只读 README，必须至少生成 repo map、entrypoints、tests、architecture insights、reuse / avoid notes；
- Issue Delta 每条 issue 必须有 source artifact / evidence / target module / acceptance criteria；
- 删除 mini-code-agent 专用模板作为产品路径；保留时只能作为 test fixture 或 documented fallback；
- 如果 LLM 编译失败，页面必须显示 blocked / fallback provenance，不能静默生成模板任务。

### Slice 3: Issue-to-Agent 主线

目标：用户能清楚控制“就跑当前 issue”。

必须做到：

- Issue detail 明确显示 selected agent、backend、runtime capability、target repo、handoff；
- Assign 后该 assignment 出现在 agent task queue；
- Start daemon 默认 scoped 到当前 assignment；
- daemon 不抢跑旧 assignment；
- agent activity / issue detail / runs / inbox 对同一 assignment 显示一致状态。

### Slice 4: Real Backend Attempt

目标：真实 Codex / Claude 必须被尝试，或产生可解释 blocker。

必须做到：

- Workbench 启动或连接 daemon 时确认 runtime authorization；
- Codex / Claude command availability、login/config/quota/gate 状态可见；
- handoff file 可打开；
- execution result 捕获 stdout / stderr / exit code / provider failure kind；
- changed files / git diff / tests / review 全部回流；
- 无真实执行时只能是 `BLOCKED_WITH_EVIDENCE`。

### Slice 5: Closure Evidence

目标：最终证据回答一个问题：目标项目版本有没有推进。

必须做到：

- 生成 `closure-result.json`；
- 如果真实执行成功，必须包含 changed files、diff、test result、review verdict；
- 如果 blocked，必须包含 blocker、用户下一步动作、是否可重试；
- Workbench 能从 current version 页面打开这些 evidence；
- 不能用 CLI-only evidence 替代浏览器链路证据。

## 验收

唯一产品验收：

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 scripts/verify_dogfood_browser.sh --real
```

该脚本必须驱动真实 Workbench 浏览器路径。它不能通过 CLI / direct API /
manual `.ariadne` JSON edits 来替代用户动作。

通过标准：

```text
status: REAL_CLOSED
```

允许的非通过标准：

```text
status: BLOCKED_WITH_EVIDENCE
```

但 blocker 必须是外部状态，例如：

- Codex / Claude CLI 不可用；
- 未登录；
- quota / rate limit；
- `ARIADNE_ENABLE_EXTERNAL_EXECUTION` 未开启；
- target repo 权限或 git 状态阻塞。

系统内部没实现、按钮没 action、source 没分析、issue 没生成、daemon 抢跑旧任务、
handoff 为空、evidence 没回流，都不能记为外部 blocker。

## 执行纪律

每个实现 PR 必须说明它推进了上述哪个 slice。

不接受：

- “新增 endpoint”但浏览器链路没变；
- “新增页面”但页面不能操作；
- “新增 agent 名称”但没有 artifact / state transition；
- “测试通过”但 dogfood 链路没推进；
- “blocked ok”但 blocker 是产品没实现。

接受：

- 用户在浏览器里少一步；
- current version 状态更清楚；
- source-to-issue 更真实；
- assignment 更可控；
- real Codex / Claude attempt 更可见；
- evidence 更完整。

## 必读证据

实施本阶段前必须读：

```text
docs/evidence/multica-downstream-parity/closure-result.json
docs/architecture/multica_downstream_parity_matrix.md
docs/architecture/multica_agent_work_management_digest.md
docs/reviews/grill-workflows/results/2026-06-24-final-41-grill-list.md
```

结论：下层 Multica-style skeleton 已经存在。下一步不是继续证明 skeleton，而是把
上层 knowledge orchestration 和下层 agent work-management 锁进同一条浏览器
Project Version Delivery 产品链路。
