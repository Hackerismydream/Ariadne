# Phase 8 Handoff: LangGraph Source-to-Issue Agent Pipeline

> **For Codex:** 先读 `AGENTS.md`（会被更新为 Phase 8），再读本文档。ADR 见 `docs/adr/ADR-0005-langgraph-source-to-issue-pipeline.md`。

## 背景

Phase 1-6 已合并到 main。Workbench 的 UI、API、lifecycle 全部就绪。但 source-to-issue pipeline 的核心——`issue_compiler.py`——仍然是 100% 模板：关键词匹配 "mini code" → 10 个固定 task，否则 → 3 个 generic task。没有 LLM 参与。

**Phase 8 的目标：** 用 LangGraph StateGraph 替换 `compile_issue_specs()` 为三阶段 LLM pipeline（per-source analysis → cross-source synthesis → goal-driven issue compilation），并保留现有模板作为 deterministic fallback。

## 核心约束

1. **Drop-in replacement：** 新函数 `compile_issue_specs_langgraph()` 与现有 `compile_issue_specs()` **同签名同返回类型**
2. **不改 HTTP 接口：** `/api/issue-factory/preview`、`/api/issue-factory/{id}/apply`、`/api/issue-factory/{id}/refresh` 不变
3. **不改前端：** PlanChangesPage 不需要改
4. **Fallback 保证输出：** 无 API key 时跳过 graph 直接用现有模板；LLM 质量不够时 retry 2 次后 fallback 到模板
5. **新增依赖最小：** 只加 `langgraph>=0.2` + `langchain-core>=0.3`，不加 `langchain-openai`、`langsmith`、`langchain-community`
6. **复用现有 DeepSeekClient：** 通过 thin adapter 适配 LangGraph，不引入新 LLM transport

## Graph 拓扑

```
START → prepare_sources → analyze_source ↺ (loop per source)
      → synthesize → compile_issues → quality_gate
        → passes (≥0.7): END
        → retry (< max): compile_issues
        → fallback (exhausted): fallback_compile → END
```

**Nodes (6):**
| Node | LLM? | Model | 职责 |
|---|---|---|---|
| `prepare_sources` | No | — | IssueFactoryContext → source_tasks queue + artifact_payloads |
| `analyze_source` | Yes | deepseek-v4-flash | 提取 per-source claims/patterns/risks |
| `synthesize` | Yes | deepseek-v4-pro | 跨 source 聚合 themes/contradictions/gaps |
| `compile_issues` | Yes | deepseek-v4-pro | goal-driven task decomposition from synthesis |
| `quality_gate` | No | — | 验证结构完整性、覆盖率、无重复 |
| `fallback_compile` | No | — | 调用现有 `_compile_mini_code_agent_specs` / `_compile_generic_specs` |

**Conditional edges (2):**
```python
# After analyze_source
def has_more_sources(state) -> Literal["analyze_source", "synthesize"]:
    return "analyze_source" if state["current_source_index"] < len(state["source_tasks"]) else "synthesize"

# After quality_gate
def should_retry_or_accept(state) -> Literal["accept", "retry", "fallback"]:
    if state["quality_score"] >= 0.7: return "accept"
    if state["compile_attempts"] >= state["max_compile_attempts"]: return "fallback"
    return "retry"
```

## State 定义

```python
from typing import TypedDict, Annotated, Literal
from operator import add

class SourceInsight(TypedDict):
    source_id: str
    source_type: str
    summary: str
    key_claims: list[str]       # 3-8 semantic assertions with file references
    reusable_patterns: list[str]
    risks: list[str]
    confidence: float           # 0.0-1.0

class SynthesisTheme(TypedDict):
    label: str
    contributing_sources: list[str]
    claims: list[str]
    priority_signal: Literal["high", "medium", "low"]
    affected_modules: list[str]

class PipelineState(TypedDict):
    # Inputs
    context_fingerprint: str
    goal_title: str
    north_star: str
    target_project_id: str
    source_tasks: list[dict]
    artifact_payloads: list[dict]
    evidence_ids: list[str]

    # Per-source accumulator
    source_insights: Annotated[list[SourceInsight], add]

    # Synthesis
    themes: list[SynthesisTheme]

    # Compilation
    compiled_specs: list[dict]  # serialized CompiledIssueSpec

    # Quality gate
    quality_score: float
    quality_issues: list[str]
    compile_attempts: int
    max_compile_attempts: int

    # Control
    current_source_index: int
    used_fallback: bool
    error: str | None
```

## LLM Adapter

**不用 `langchain-openai`。** Wrap 现有 `DeepSeekClient`：

```python
# ariadne_ltb/application/langgraph_pipeline/llm_adapter.py
from ariadne_ltb.llm import DeepSeekClient

class DeepSeekAdapter:
    def __init__(self, model: str = "deepseek-v4-pro"):
        self._client = DeepSeekClient(model=model)

    def invoke(self, prompt: str, schema_name: str) -> dict:
        return self._client.complete_json(prompt, schema_name)
```

## Node 实现模式

每个 LLM node 遵循相同的 error handling 模式：

```python
def analyze_source_node(state: PipelineState) -> dict:
    task = state["source_tasks"][state["current_source_index"]]
    prompt = build_analyze_prompt(task, state["goal_title"])
    
    for attempt in range(3):
        try:
            raw = adapter.invoke(prompt, "source_insight")
            insight = SourceInsight(**raw)  # validate
            return {
                "source_insights": [insight],
                "current_source_index": state["current_source_index"] + 1,
            }
        except LLMClientError as exc:
            if not exc.error.retryable or attempt == 2:
                break
        except (ValidationError, KeyError, TypeError):
            continue

    # Deterministic fallback for this source
    return {
        "source_insights": [_deterministic_insight(task)],
        "current_source_index": state["current_source_index"] + 1,
    }
```

## Quality Gate 规则

```python
def quality_gate_node(state: PipelineState) -> dict:
    specs = state["compiled_specs"]
    issues = []
    
    if len(specs) < 3: issues.append("too_few_issues")
    if len(specs) > 20: issues.append("too_many_issues")
    if len(set(s["title"] for s in specs)) < len(specs): issues.append("duplicate_titles")
    for spec in specs:
        if len(spec.get("acceptance_criteria", [])) < 2: issues.append(f"weak_criteria:{spec['title'][:30]}")
        if not spec.get("affected_modules"): issues.append(f"no_modules:{spec['title'][:30]}")
        if len(spec.get("title", "")) < 10: issues.append(f"short_title:{spec['title']}")
    
    # Coverage: every theme should map to at least one spec
    theme_labels = {t["label"] for t in state["themes"]}
    covered = set()
    for spec in specs:
        for theme in theme_labels:
            if theme.lower() in spec.get("reason", "").lower():
                covered.add(theme)
    uncovered = theme_labels - covered
    if uncovered: issues.append(f"uncovered_themes:{len(uncovered)}")
    
    score = 1.0 - (len(issues) * 0.15)
    return {"quality_score": max(0.0, score), "quality_issues": issues}
```

## 集成点

**`issue_factory.py` 第 90 行（唯一改动）：**

```python
# Before:
tasks = compile_issue_specs(self.store, title=title, north_star=north_star, context=context)

# After:
from ariadne_ltb.application.langgraph_pipeline import compile_issue_specs_langgraph
tasks = compile_issue_specs_langgraph(self.store, title=title, north_star=north_star, context=context)
```

**Public API (`__init__.py`)：**

```python
import os
from ariadne_ltb.application.issue_compiler import compile_issue_specs

def compile_issue_specs_langgraph(store, *, title, north_star, context):
    if not os.environ.get("DEEPSEEK_API_KEY"):
        return compile_issue_specs(store, title=title, north_star=north_star, context=context)
    
    from .graph import build_issue_compilation_graph
    from .state import prepare_initial_state
    
    graph = build_issue_compilation_graph(store)
    initial = prepare_initial_state(title, north_star, context, store)
    result = graph.invoke(initial)
    
    if result.get("used_fallback") or result.get("error"):
        return compile_issue_specs(store, title=title, north_star=north_star, context=context)
    
    from ariadne_ltb.application.issue_compiler import CompiledIssueSpec
    return [CompiledIssueSpec(**spec) for spec in result["compiled_specs"]]
```

## 文件结构

```
ariadne_ltb/application/langgraph_pipeline/
├── __init__.py              # compile_issue_specs_langgraph() public API
├── state.py                 # PipelineState + SourceInsight + SynthesisTheme + prepare_initial_state()
├── graph.py                 # build_issue_compilation_graph() — nodes + edges
├── nodes/
│   ├── __init__.py
│   ├── prepare.py           # prepare_sources_node
│   ├── analyze.py           # analyze_source_node (LLM + deterministic fallback)
│   ├── synthesize.py        # synthesize_node (LLM)
│   ├── compile.py           # compile_issues_node (LLM)
│   ├── quality.py           # quality_gate_node (deterministic)
│   └── fallback.py          # fallback_compile_node (wraps existing templates)
├── prompts.py               # All prompt templates (separate from logic)
├── llm_adapter.py           # DeepSeekAdapter thin wrapper
└── errors.py                # LLMUnavailableError
```

## Prompt 设计（核心）

### analyze_source prompt (Stage 1)

```
You are analyzing a reference source for an AI Builder project.

Project goal: {goal_title} — {north_star}

Source type: {source_type}
Source content:
{content[:6000]}

Artifact metadata:
{artifact_payload_summary}

Extract:
1. key_claims: 3-8 specific, verifiable assertions about what this source teaches.
   Each claim must cite a specific file, section, or quote.
2. reusable_patterns: architectural patterns or decisions relevant to the project goal.
3. risks: what NOT to copy or potential pitfalls from this source.

Return JSON: {"source_id": "...", "source_type": "...", "summary": "...", "key_claims": [...], "reusable_patterns": [...], "risks": [...], "confidence": 0.0-1.0}
```

### synthesize prompt (Stage 2)

```
You have analyzed {n} sources for the project:
Goal: {goal_title} — {north_star}

Source insights:
{formatted_insights}

Synthesize into themes that inform task decomposition:
1. What themes emerge across all sources? (group related claims)
2. What contradictions or tensions exist between sources?
3. What coverage gaps exist (goal needs it, no source addresses it)?
4. For each theme, suggest which target modules it affects.

Return JSON: {"themes": [{"label": "...", "contributing_sources": [...], "claims": [...], "priority_signal": "high|medium|low", "affected_modules": [...]}]}
```

### compile_issues prompt (Stage 3)

```
You are a Build Lead decomposing a project version into implementation issues.

Goal: {goal_title} — {north_star}
Target project: {target_project_id}

Synthesized themes:
{formatted_themes}

Available evidence: {evidence_ids}

Rules:
- Generate 5-15 issues
- Each issue must be completable in one Codex or Claude Code pass (< 2 hours of agent work)
- Acceptance criteria must be testable without human judgment
- Cite which theme/evidence supports each task
- Specify affected_modules (actual file paths in target project)
- Order by dependency (earlier issues don't depend on later ones)
- Priority: P0 (must-have for version), P1 (should-have), P2 (nice-to-have)

Return JSON: {"issues": [{"title": "...", "reason": "...", "priority": "P0|P1|P2", "affected_modules": [...], "acceptance_criteria": [...], "evidence_refs": [...], "depends_on": [...]}]}
```

## 依赖变更

```toml
# pyproject.toml
dependencies = [
  # ... existing ...
  "langgraph>=0.2",
  "langchain-core>=0.3",
]
```

## 不做（硬边界）

- 不改 HTTP routes
- 不改前端代码
- 不加 `langchain-openai`、`langsmith`、`langchain-community`
- 不加 MemorySaver checkpoint（不需要）
- 不实现 human-in-the-loop interrupt（v2 feature）
- 不改 `source_analysis.py`（Phase 8 只替换 issue compilation，不改 source analysis）
- 不实现 async（保持现有 sync 风格）
- 不删除旧 `issue_compiler.py`（保留作为 fallback）

## Testing 策略

1. **Node unit tests** — 每个 node 是纯函数 `(PipelineState) -> dict`，用 fixture state 测试
2. **FakeTransport** — 复用 `tests/` 中已有的 `FakeTransport` 模式 mock LLM 调用
3. **Graph integration** — 用 FakeTransport 跑完整 graph，验证 output 是 valid `list[CompiledIssueSpec]`
4. **Fallback path** — 不设 `DEEPSEEK_API_KEY`，验证直接返回 deterministic 结果
5. **现有测试不能破** — `test_issue_factory_compiler.py` 仍然 green（走 fallback 路径）

新增测试文件：
- `tests/test_langgraph_pipeline_nodes.py` — node 单元测试
- `tests/test_langgraph_pipeline_graph.py` — graph 集成测试

## 验收标准

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m pytest
ruff check .
cd frontend/ariadne-workbench && npm run build
```

### 无 API key（CI 环境）
- 所有测试通过，pipeline 走 deterministic fallback
- `test_issue_factory_compiler.py` 原有测试不变

### 有 API key（本地验证）
```bash
export DEEPSEEK_API_KEY=your_key
python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8766
```
- 浏览器：#sources → 添加 URL → #plan-changes → Generate Issue Delta
- 验证：生成的 issues 是**根据 source 内容推理的**（不是固定 10 task 模板）
- 验证：每个 issue 的 reason 引用了具体的 source evidence
- 验证：acceptance criteria 是 per-issue 定制的（不是所有 issue 共享同一组）

## 启动命令

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8766
```

## 分支和 PR

- Branch: `codex/phase8-langgraph-source-pipeline`
- PR title: `Phase 8: LangGraph source-to-issue agent pipeline`
- PR base: `main`
