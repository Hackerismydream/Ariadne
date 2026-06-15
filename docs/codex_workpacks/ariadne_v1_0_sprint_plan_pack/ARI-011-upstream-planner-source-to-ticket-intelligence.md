# ARI-011 — Upstream Planner and Source-to-Ticket Intelligence

## 目标

让 Ariadne 的上游能力更接近 “Learning-to-Build”，而不是只靠固定 fixture 映射。

当前问题：

```text
source ingestion 仍然偏规则
GitHub README fixture 固定生成 demo-todo export-json
LLM client 存在但不是主流程
```

本轮目标：

1. 普通 markdown 输入也能生成合理 Build Packet。
2. Planner 能提取 evidence。
3. LLM Planner 是可选路径。
4. 生成的 Ticket / Packet 更像从知识到构建的转换结果。

## 需要实现的能力

### 1. Source parser 增强

对任意 markdown：

1. 提取 H1 作为标题。
2. 提取 headings。
3. 提取 2-5 条 evidence snippets。
4. 根据内容判断 source type。
5. 提取可能的 action verbs，例如 implement / add / compare / evaluate / build。
6. 生成 source summary。

不要只依赖文件名。

### 2. DeterministicPlanner 增强

它应该基于 source 内容和当前 Project Space 判断：

```text
build_decision
tasks
acceptance_criteria
affected_modules
risks
assumptions
```

基本规则：

- 包含 “implementation / CLI / GitHub / README / feature” → code_task。
- 包含 “evaluation / benchmark / metric / paper” → experiment。
- 包含 “architecture / decision / tradeoff” → doc_update 或 architecture_change。
- 内容不明确 → watchlist。

### 3. LLMPlanner 接入

如果已有 `DeepSeekClient` / `default_llm()`，请把它接入 planner。

命令：

```bash
ari ticket plan ARI-003 --planner deterministic
ari ticket plan ARI-003 --planner llm
ari ingest examples/sources/*.md --planner deterministic
ari ingest examples/sources/*.md --planner llm
```

当用户选择 `--planner llm`：

- 如果没有 key，生成 blocked planner artifact，清晰提示缺 key；
- 不要崩溃；
- 不要让测试依赖 key；
- LLM 输出必须 JSON validate；
- JSON invalid 时保存 planner error artifact。

### 4. Build Packet 质量

新增轻量评分：

```python
evidence_coverage_score
task_clarity_score
acceptance_criteria_score
scope_risk_score
overall_quality
```

可以放在 metadata 或新增 `BuildPacketQualityReport`。

用于：

1. Reviewer 参考。
2. Board 展示。
3. Next tickets 生成。

### 5. 当前 Ariadne repo 作为输入

新增一个示例 source：

```text
examples/sources/ariadne_self_improvement_note.md
```

内容应该描述 Ariadne 当前需要改进 daemon / retry / handoff / real codex。

Planner 应能从它生成 code_task 或 architecture_change。

## 验收标准

测试覆盖：

1. arbitrary markdown 能生成 evidence snippets。
2. H1 title extraction。
3. DeterministicPlanner 生成 code_task / experiment / doc_update。
4. LLM planner 无 key 时 graceful blocked。
5. invalid JSON 保存 error artifact。
6. Build Packet quality report 生成。
7. Board 展示 quality summary。
8. 不破坏已有 fixture 行为。

## Board 要求

Board 中 Build Packet 区块展示：

```text
quality score
evidence count
task clarity
scope risk
planner mode
```

## 文档要求

README 说明：

```bash
ari ingest my_note.md --planner deterministic
ari ticket plan ARI-003 --planner llm
```

并说明默认不需要 LLM key。
