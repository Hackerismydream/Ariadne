# Project Resource Schema

```json
{
  "id": "",
  "resource_type": "github_repo|local_directory|source_document|feishu_space|memory_dir",
  "resource_ref": {},
  "label": "",
  "created_at": ""
}
```

Examples:

```json
{
  "resource_type": "local_directory",
  "resource_ref": {
    "local_path": "/absolute/path/to/project"
  },
  "label": "demo target project"
}
```

```json
{
  "resource_type": "source_document",
  "resource_ref": {
    "path": "examples/sources/blog_multica_lessons.md",
    "source_type": "blog"
  },
  "label": "Multica lessons blog"
}
```
