# ARI-015 Architecture Freeze with Multica Mapping

## 目标

冻结 Ariadne v1.x 技术架构，以 Multica 为固定对标，明确 Ariadne 的能力面、系统分层、核心对象和后续路线。

## 背景

当前 Ariadne 已经有很多能力，但文档容易散。需要一份架构冻结文档，帮助后续 demo、实现和面试讲解。

## 交付

新增或更新：

```text
docs/architecture/ARIADNE_V1_ARCHITECTURE.md
docs/architecture/ARIADNE_V1_OBJECT_MODEL.md
docs/architecture/ARIADNE_V1_MULTICA_MAPPING.md
docs/architecture/ARIADNE_V1_CAPABILITY_SURFACE.md
docs/demo/ARIADNE_V1_DEMO_CONTRACT.md
README.md
docs/development_report.md
```

## 必须包含

```text
目标用户
产品定位
Multica 对标分析
Ariadne 与 Multica 映射表
系统分层
核心对象模型
主运行流程
Agent Teammate Mode
Goal-driven Multi-Agent Build Team 定位
fake-codex / Codex / Claude 边界
安全 gate
当前限制
后续路线
```

## Mermaid 图

必须包含：

```text
系统分层图
主链路时序图
对象关系图
Multica vs Ariadne 映射图
Codex safety gate 图
```

## 验收

```bash
pytest
ruff check .
python3.11 -m ariadne_ltb.cli doctor v1
python3.11 -m ariadne_ltb.cli export board
```

