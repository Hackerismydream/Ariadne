# ARI-021 Project Resource Boundaries

## 目标

扩展 ProjectResource，使 Agent 获取上下文和执行时有明确资源边界。

## 新资源类型

```text
local_directory
github_repo
feishu_space
memory_store
source_collection
target_project
```

## 字段

```text
resource_type
resource_ref
label
access_mode
allowed_paths
blocked_paths
requires_confirmation
```

access_mode：

```text
read_only
read_write
execute
write_plan_only
```

## CLI

```bash
ari resource list
ari resource add-local ./path --label target --access read_write
ari resource show <resource_id>
```

## 验收

Agent 执行时必须引用 target_project resource，而不是自由路径。

