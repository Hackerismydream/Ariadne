from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

IGNORE_DIRS = {
    ".git",
    "node_modules",
    "vendor",
    "dist",
    "build",
    ".venv",
    "__pycache__",
    ".ruff_cache",
    ".pytest_cache",
}
MANIFESTS = ["pyproject.toml", "package.json", "go.mod", "Cargo.toml", "requirements.txt", "uv.lock"]


@dataclass(frozen=True)
class RepositoryScan:
    summary: str
    top_level: list[str]
    manifests: list[str]
    test_paths: list[str]
    entrypoints: list[str]
    selected_files: list[str]
    warnings: list[str] = field(default_factory=list)


def scan_repository(root: Path, *, max_files: int = 3000, max_selected_files: int = 40) -> RepositoryScan:
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(str(root))
    all_files: list[Path] = []
    file_limit_hit = False
    for path in root.rglob("*"):
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if path.is_file():
            all_files.append(path)
        if len(all_files) > max_files:
            file_limit_hit = True
            break
    rel_files = [path.relative_to(root).as_posix() for path in all_files]
    top_level = sorted({Path(item).parts[0] for item in rel_files if Path(item).parts})
    manifests = sorted(item for item in rel_files if Path(item).name in MANIFESTS)
    test_paths = sorted(item for item in rel_files if _is_test_file(item))
    entrypoints = sorted(
        dict.fromkeys([
            *(item for item in rel_files if _is_entrypoint(item)),
            *_manifest_entrypoints(root),
        ])
    )
    selected = _select_files(rel_files, manifests, test_paths, entrypoints, max_selected_files)
    summary = _read_readme(root) or f"Repository with {len(rel_files)} readable files."
    warnings = ["scan_file_limit_hit"] if file_limit_hit else []
    return RepositoryScan(summary, top_level, manifests, test_paths, entrypoints, selected, warnings)


def infer_test_commands(manifests: list[str], test_paths: list[str]) -> list[str]:
    if not test_paths:
        return []
    if "pyproject.toml" in manifests or "requirements.txt" in manifests:
        return ["python3.11 -m pytest"]
    if "package.json" in manifests:
        return ["npm test"]
    if "go.mod" in manifests:
        return ["go test ./..."]
    if "Cargo.toml" in manifests:
        return ["cargo test"]
    return ["python3.11 -m pytest"]


def _read_readme(root: Path) -> str:
    for name in ["README.md", "readme.md", "README.rst"]:
        path = root / name
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8", errors="replace")[:1200]
    return ""


def _is_test_file(path: str) -> bool:
    p = Path(path)
    return "tests" in p.parts or p.name.startswith("test_") or p.name.endswith(".test.ts") or p.name.endswith(".spec.ts")


def _is_entrypoint(path: str) -> bool:
    name = Path(path).name
    return name in {"main.py", "cli.py", "__main__.py", "index.ts", "index.js", "main.ts", "main.js"}


def _manifest_entrypoints(root: Path) -> list[str]:
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return []
    entrypoints: list[str] = []
    for line in pyproject.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if "=" in stripped and ":" in stripped and not stripped.startswith("["):
            entrypoints.append(stripped)
    return entrypoints


def _select_files(
    rel_files: list[str],
    manifests: list[str],
    tests: list[str],
    entrypoints: list[str],
    limit: int,
) -> list[str]:
    ordered: list[str] = []
    for bucket in [["README.md", "readme.md"], manifests, entrypoints, tests[:10], rel_files[:20]]:
        for item in bucket:
            if item in rel_files and item not in ordered:
                ordered.append(item)
    return ordered[:limit]
