# ADR-0005: LangGraph-based Source-to-Issue Agent Pipeline

## Status

Proposed (pending Phase 6/7 completion)

## Context

Ariadne 的 source-to-issue pipeline 当前是 deterministic template（`issue_compiler.py` 用关键词匹配选择 10-task 或 3-task 模板，无 LLM 调用）。这对校招 Agent 岗面试没有竞争力，也无法根据不同外部输入生成有差异的 issue set。

目标用户：国内互联网大厂 Agent 开发岗。技术选型需要体现对主流 Agent 编排框架的深度工程理解。

## Decision

引入 **LangGraph** 作为 source-to-issue pipeline 的编排框架。理由：

1. **面试信号最强** — LangGraph 是 2026 年 Agent 岗位最常见的技术栈要求（字节、阿里、腾讯 AI Lab 均有 LangGraph 相关 JD）
2. **有向状态图** — 不是 chain-of-calls，有条件分支、循环重试、checkpoint 容错
3. **可观测** — LangSmith 或自研 event log 接入
4. **与 Ariadne 产品集成** — Graph output → BacklogPreview → Issue Board，不是 notebook demo
5. **工程级** — 跑在 FastAPI 里的 production pipeline，有 checkpoint、retry、quality gate

不选 PydanticAI 的原因：虽然更轻量且跟现有 Pydantic 栈契合，但面试展示度不如 LangGraph（面试官不会因为你用 PydanticAI 觉得你懂 Agent 编排）。

不选 CrewAI 的原因：execution trace 不可靠，async 问题多，社区报告质量问题。

不选 DSPy 的原因：核心优势是 prompt 自动优化，Ariadne 场景需要的是可控的 multi-step pipeline。

## Architecture

### Three-Stage Pipeline as LangGraph StateGraph

```
START
  → route_source (conditional: pick next source type)
    → analyze_repo (LLM: extract patterns, claims, risks from repo)
    → analyze_text (LLM: extract claims from text/paper/blog)
    → analyze_codebase (deterministic: target project snapshot)
  → validate_evidence (quality gate: confidence threshold)
    → [retry loop if confidence < 0.6, max 2 retries]
  → synthesize_sources (LLM: cross-source themes, contradictions, gaps)
  → compile_issues (LLM: goal-driven task decomposition)
  → rank_and_validate (deterministic: topological sort + feasibility)
  → END → BacklogPreview
```

### State Design

```python
class PipelineState(TypedDict):
    # Input
    goal_title: str
    goal_north_star: str
    source_ids: list[str]
    target_project_id: str | None
    
    # Stage 1 (accumulated per source)
    analyses: Annotated[list[SourceAnalysis], operator.add]
    pending_source_ids: list[str]
    current_source_id: str | None
    
    # Quality gate
    low_confidence_sources: list[str]
    retry_count: int
    
    # Stage 2
    synthesis: Synthesis | None
    
    # Stage 3
    compiled_issues: list[CompiledIssue]
    validation_errors: list[str]
```

### Key Design Decisions

| Decision | Rationale |
|---|---|
| State accumulation via `Annotated[list, operator.add]` | 每个 source 分析完追加到 analyses，不覆盖 |
| Conditional routing in `route_source` | 按 source_type 分发到不同分析 node |
| Quality gate with retry loop | validate_evidence → re_analyze 循环，max 2 次 |
| MemorySaver checkpoint | 分析到一半可断点续跑（source 多时有意义） |
| Synthesis 作为独立 node | 不是把所有 source 塞给一个 prompt，而是先分析再综合 |
| 最终 rank_and_validate 是 deterministic | LLM 负责创意生成，topological sort 确保依赖正确 |

### Structured Output (面试重点)

每个 LLM node 用 `llm.with_structured_output(PydanticModel)` 强制输出类型安全：

```python
class SourceAnalysis(BaseModel):
    source_id: str
    claims: list[EvidenceClaim]    # locator + claim + confidence
    patterns: list[str]
    risks: list[str]
    reuse_notes: list[str]

class Synthesis(BaseModel):
    themes: list[str]
    contradictions: list[str]
    coverage_gaps: list[str]
    decomposition_strategy: str
    confidence: float

class CompiledIssue(BaseModel):
    title: str
    reason: str                    # must cite evidence
    priority: Literal["P0", "P1", "P2"]
    affected_modules: list[str]
    acceptance_criteria: list[str]
    evidence_refs: list[str]
    depends_on: list[str]
```

### Integration with Existing Code

```python
# issue_factory.py — preview() 方法中替换 compile_issue_specs 调用
from ariadne_ltb.agents.source_to_issue_graph import build_source_to_issue_graph

graph = build_source_to_issue_graph()
result = graph.invoke({
    "goal_title": title,
    "goal_north_star": north_star,
    "source_ids": [s.id for s in context.sources],
    "target_project_id": payload.target_project_id,
    "pending_source_ids": [s.id for s in context.sources],
    "analyses": [],
    "retry_count": 0,
})
tasks = result["compiled_issues"]
# → 转换为 BacklogOperation（复用现有逻辑）
```

### File Structure

```
ariadne_ltb/
├── agents/
│   ├── __init__.py
│   ├── source_to_issue_graph.py    # StateGraph 定义 + graph.compile()
│   ├── state.py                    # PipelineState + Pydantic models
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── route_source.py
│   │   ├── analyze_repo.py         # LLM call: repo → SourceAnalysis
│   │   ├── analyze_text.py         # LLM call: text → SourceAnalysis
│   │   ├── analyze_codebase.py     # Deterministic: snapshot
│   │   ├── validate_evidence.py    # Quality gate
│   │   ├── synthesize.py           # LLM call: all analyses → Synthesis
│   │   ├── compile_issues.py       # LLM call: synthesis + goal → issues
│   │   └── rank_validate.py        # Deterministic: topological sort
│   └── prompts.py                  # Prompt templates (分离便于调优)
tests/
├── test_source_to_issue_graph.py   # Graph integration tests
├── test_graph_nodes_unit.py        # Per-node unit tests (mocked LLM)
```

### LLM Provider

使用已有 DeepSeek 客户端，通过 LangChain 的 OpenAI-compatible wrapper 接入 LangGraph：

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="deepseek-v4-pro",
    base_url="https://api.deepseek.com/v1",
    api_key=os.environ["DEEPSEEK_API_KEY"],
)
```

Fallback: `deepseek-v4-flash` for Stage 1 text analysis (cheaper, sufficient quality).

### Token Budget

- Stage 1: ~2k tokens/source × 10 sources = 20k input
- Stage 2: ~8k tokens (all evidence summaries)
- Stage 3: ~4k tokens (synthesis + goal)
- Total: ~32k input + ~4k output ≈ ¥0.1-0.3 per full pipeline run

### What This Demonstrates in Interview

| 面试考察点 | 如何体现 |
|---|---|
| Agent 状态机设计 | LangGraph StateGraph 有条件边、循环重试、checkpoint |
| Multi-agent 协作 | 5 个 typed analysis nodes + synthesis + compilation |
| Structured output | TypedDict state + `with_structured_output` + Pydantic validation |
| LLM 不可靠性处理 | Quality gate + retry loop + confidence threshold |
| 工程级 Agent 系统 | 跑在 FastAPI 里，output 回流 Issue Board，不是 demo |
| 可观测性 | LangSmith tracing 或 runtime_event 自研日志 |
| 增量更新 | payload_hash fingerprint + checkpoint = 加新 source 不全量重跑 |

## Consequences

### Positive

- 面试时可以从"产品使用场景"讲到"图设计"讲到"quality gate 为什么这样做"，有深度
- Source-to-issue pipeline 从模板变成真实 AI 推理
- Issue quality 显著提升（有 evidence 支撑的 acceptance criteria）

### Negative

- 引入 `langgraph` + `langchain-openai` 依赖（~10MB）
- 需要 DeepSeek API key 才能跑 pipeline（离线 fallback 保留旧模板路径）
- Pipeline 执行时间从 <1s（模板）变为 10-30s（LLM calls）

### Mitigation

- 保留 `_compile_generic_specs()` 作为 offline fallback（无 API key 时降级）
- `MemorySaver` checkpoint 保证中途失败不丢已分析的 source
- 前端 lifecycle status 已有 analyzing → analyzed → failed 展示，用户能看到进度

## Implementation Phase

建议作为 **Phase 8** 实施（Phase 7 browser dogfood 完成后），或如果 Phase 7 需要更好的 issue quality 来证明闭环，可以提前到 Phase 7 之前。

### 依赖

- Phase 5 ✅ (Sources + Plan Changes 前端已就绪)
- Phase 6 ✅ (Lifecycle hardening 确保 pipeline 结果正确回流)
- `pip install langgraph langchain-openai`
- `DEEPSEEK_API_KEY` environment variable

### Estimated Effort

| 工作 | 行数 |
|---|---|
| `agents/state.py` | ~60 |
| `agents/nodes/*.py` (7 nodes) | ~250 |
| `agents/source_to_issue_graph.py` | ~40 |
| `agents/prompts.py` | ~80 |
| Integration in `issue_factory.py` | ~30 |
| Tests | ~150 |
| **Total** | **~610 lines** |
