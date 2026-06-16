# ARI-023 Review and Evaluation Agent

## 目标

增强 Reviewer，从规则检查升级为更完整的质量评估 Agent。

## 能力

```text
Build Packet quality scoring
Execution result review
Diff scope review
Acceptance criteria alignment
Test coverage review
Risk scoring
Human review recommendation
Retry / next ticket recommendation
```

## 指标

```text
evidence_coverage
task_clarity
acceptance_criteria_quality
scope_risk
execution_success
test_success
changed_file_scope
retry_rate
human_intervention_count
```

## 输出

ReviewReport 应增加：

```text
quality_scores
risk_scores
human_review_required
recommended_next_action
suggested_retry_policy
```

## 验收

review artifact 必须能用于面试展示：

```text
为什么 pass
为什么 blocked
风险是什么
下一步是什么
```

