from __future__ import annotations

from typing import Any


def validate_dag(state: dict[str, Any]) -> dict[str, Any]:
    issues = [dict(item) for item in state.get("grounded_issues", [])]
    titles = {str(item.get("title") or "") for item in issues}
    clean: list[dict[str, Any]] = []
    for item in issues:
        depends_on = [str(dep) for dep in item.get("depends_on", []) if str(dep) in titles]
        clean.append(_normalize_issue(item | {"depends_on": depends_on}))
    if _has_cycle(clean):
        return {"validated_issues": [], "quality_issues": ["dependency_cycle"]}
    return {"validated_issues": clean}


def _normalize_issue(item: dict[str, Any]) -> dict[str, Any]:
    affected_modules = [str(value) for value in item.get("affected_modules", []) if str(value).strip()]
    acceptance_criteria = [
        str(value) for value in item.get("acceptance_criteria", []) if str(value).strip()
    ]
    if not affected_modules:
        affected_modules = ["src/", "tests/"]
    if len(acceptance_criteria) < 2:
        acceptance_criteria.extend(
            [
                "The change is reachable from the Ariadne-managed target project path.",
                "Tests or documented verification cover the completed behavior.",
            ][: 2 - len(acceptance_criteria)]
        )
    return item | {
        "affected_modules": affected_modules,
        "acceptance_criteria": acceptance_criteria,
    }


def _has_cycle(issues: list[dict[str, Any]]) -> bool:
    graph = {str(item.get("title") or ""): set(item.get("depends_on", [])) for item in issues}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for dep in graph.get(node, set()):
            if visit(dep):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph)
