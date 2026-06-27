from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ariadne_ltb.application.build_context import IssueFactoryContext
from ariadne_ltb.models import SourceArtifact, SourceEvidence
from ariadne_ltb.storage import AriadneStore


@dataclass(frozen=True)
class CompiledIssueSpec:
    title: str
    reason: str
    priority: str
    affected_modules: list[str]
    acceptance_criteria: list[str]
    evidence_refs: list[str]
    owner_agent: str = "Build Lead"
    build_decision: str = "code_task"
    risks: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ArtifactBuckets:
    repository_payloads: list[dict[str, Any]]
    text_payloads: list[dict[str, Any]]
    target_payload: dict[str, Any]


@dataclass(frozen=True)
class TargetShape:
    label: str
    local_path: str
    package_dir: str
    source_root: str
    tests_root: str
    docs_root: str
    selected_files: list[str]
    top_level: list[str]
    test_commands: list[str]


def compile_issue_specs(
    store: AriadneStore,
    *,
    title: str,
    north_star: str,
    context: IssueFactoryContext,
) -> list[CompiledIssueSpec]:
    artifact_payloads = [(artifact, store.load_source_artifact_payload(artifact.id)) for artifact in context.artifacts]
    buckets = _bucket_payloads(artifact_payloads)
    target = _target_shape(store, context, buckets.target_payload)
    source_summary = _source_summary(title, north_star, buckets)
    agent_or_tool_project = _mentions_any(
        source_summary.lower(),
        {"agent", "loop", "tool", "action", "observation", "diff", "review", "trajectory", "session"},
    )
    return _agent_specs(target, source_summary, context.evidence, buckets) if agent_or_tool_project else _generic_specs(
        target,
        source_summary,
        context.evidence,
        buckets,
    )


def _bucket_payloads(artifact_payloads: list[tuple[SourceArtifact, dict[str, Any]]]) -> ArtifactBuckets:
    repositories: list[dict[str, Any]] = []
    text: list[dict[str, Any]] = []
    target: dict[str, Any] = {}
    for artifact, payload in artifact_payloads:
        if artifact.artifact_type == "codebase_snapshot":
            target = payload
        elif artifact.artifact_type in {"repository_understanding", "reference_project_profile"}:
            repositories.append(payload)
        elif artifact.artifact_type in {"knowledge_card", "text_understanding"}:
            text.append(payload)
    return ArtifactBuckets(repository_payloads=repositories, text_payloads=text, target_payload=target)


def _target_shape(store: AriadneStore, context: IssueFactoryContext, target_payload: dict[str, Any]) -> TargetShape:
    label = context.manifest.target_project_id
    local_path = str(target_payload.get("target_path") or "")
    for resource in store.load_project_resources():
        if resource.id != context.manifest.target_project_id:
            continue
        label = resource.label or str(resource.resource_ref.get("label") or label)
        local_path = str(resource.resource_ref.get("local_path") or local_path)
        break
    top_level = _string_list(target_payload.get("top_level"))
    selected_files = _string_list(target_payload.get("selected_files"))
    package_dir = _package_dir_from_target(local_path or label, top_level, selected_files)
    source_root = "src" if "src" in top_level else package_dir
    tests_root = "tests" if "tests" in top_level or _string_list(target_payload.get("test_paths")) else "tests"
    docs_root = "docs" if "docs" in top_level else "docs"
    test_commands = _string_list(target_payload.get("test_commands")) or ["python3.11 -m pytest"]
    return TargetShape(
        label=label,
        local_path=local_path,
        package_dir=package_dir,
        source_root=source_root,
        tests_root=tests_root,
        docs_root=docs_root,
        selected_files=selected_files,
        top_level=top_level,
        test_commands=test_commands,
    )


def _agent_specs(
    target: TargetShape,
    source_summary: str,
    evidence: list[SourceEvidence],
    buckets: ArtifactBuckets,
) -> list[CompiledIssueSpec]:
    return [
        _spec(
            title=f"Map source claims into {target.label} v0.1 contract",
            reason=(
                f"{target.label} needs a reviewable first-version contract before implementation. "
                f"Source analysis says: {_truncate(source_summary, 420)}"
            ),
            modules=[f"{target.docs_root}/product-contract.md", "README.md"],
            evidence=evidence,
            keywords={"claim", "source", "guidance", "agent", "test"},
            acceptance=[
                "The target repository contains a concise v0.1 contract naming selected source claims and evidence ids.",
                "The contract states target areas, implementation boundaries, and verification commands for this Project Version.",
                "No requirement in the contract points to Ariadne internals unless Ariadne is the selected target project.",
            ],
            risks=_combined_risks(buckets),
        ),
        _spec(
            title=f"Create executable entrypoint for {target.label}",
            reason=(
                "Repository sources expose entrypoint and test-shape signals, and the target codebase snapshot "
                f"currently shows {_target_snapshot_phrase(target)}."
            ),
            modules=[
                "pyproject.toml",
                f"{target.package_dir}/__main__.py",
                f"{target.package_dir}/cli.py",
                f"{target.tests_root}/test_cli.py",
            ],
            evidence=evidence,
            keywords={"entrypoint", "cli", "package", "test", "repository"},
            acceptance=[
                "A local command or Python package entrypoint runs without external credentials.",
                "The entrypoint returns a deterministic status for a minimal task input.",
                f"`{target.test_commands[0]}` covers command wiring and failure messaging.",
            ],
        ),
        _spec(
            title=f"Implement source-backed action loop for {target.label}",
            reason=(
                "Blog and repository evidence mention agent loops, actions, observations, sessions, or tools; "
                "the target needs this behavior as a small inspectable vertical slice."
            ),
            modules=[
                f"{target.package_dir}/protocol.py",
                f"{target.package_dir}/agent_loop.py",
                f"{target.tests_root}/test_agent_loop.py",
            ],
            evidence=evidence,
            keywords={"agent", "loop", "action", "observation", "session", "tool"},
            acceptance=[
                "The loop accepts a task, emits a typed action, records an observation, and terminates with done or blocked state.",
                "The implementation is deterministic under tests and does not require a live model provider.",
                "Tests cover successful completion and blocked-state reporting.",
            ],
        ),
        _spec(
            title=f"Add bounded tool execution for {target.label}",
            reason=(
                "Repository safety and risk artifacts require local execution boundaries before a code-agent workflow "
                "can be reviewable."
            ),
            modules=[
                f"{target.package_dir}/tools/shell.py",
                f"{target.package_dir}/tools/files.py",
                f"{target.tests_root}/test_tools.py",
            ],
            evidence=evidence,
            keywords={"safety", "allowlist", "permission", "tool", "file", "shell", "risk"},
            acceptance=[
                "Shell actions reject commands outside an explicit allowlist.",
                "File actions stay inside the target repository and report rejected paths with reasons.",
                "Tests cover allowed and rejected shell/file operations.",
            ],
            risks=_combined_risks(buckets),
        ),
        _spec(
            title=f"Capture review evidence for {target.label} runs",
            reason=(
                "Source artifacts emphasize tests, diffs, review checkpoints, or trajectories; generated work is not "
                "reviewable until the target records those outputs."
            ),
            modules=[
                f"{target.package_dir}/trace.py",
                f"{target.package_dir}/evidence.py",
                f"{target.tests_root}/test_evidence.py",
            ],
            evidence=evidence,
            keywords={"diff", "review", "test", "trace", "trajectory", "evidence"},
            acceptance=[
                "A run record contains task input, actions, observations, changed files, test command, and test result.",
                "The evidence record can be serialized to disk for review without Ariadne-specific storage.",
                "Tests verify both passing and blocked run evidence.",
            ],
            priority="high",
        ),
        _spec(
            title=f"Document runnable workflow for {target.label}",
            reason=(
                "The Issue Delta must leave the selected target project with a repeatable path from setup to verification."
            ),
            modules=["README.md", f"{target.docs_root}/quickstart.md"],
            evidence=evidence,
            keywords={"readme", "quickstart", "test", "entrypoint", "workflow"},
            acceptance=[
                "README includes install, run, and test commands for the v0.1 workflow.",
                "The documented command path references target project files, not Ariadne product code.",
                "The quickstart explains how to inspect generated run evidence.",
            ],
            priority="medium",
        ),
    ]


def _generic_specs(
    target: TargetShape,
    source_summary: str,
    evidence: list[SourceEvidence],
    buckets: ArtifactBuckets,
) -> list[CompiledIssueSpec]:
    modules = _target_modules(target)
    return [
        _spec(
            title=f"Map source claims into {target.label} implementation contract",
            reason=f"Selected sources need a traceable target-project contract: {_truncate(source_summary, 420)}",
            modules=[f"{target.docs_root}/product-contract.md", "README.md"],
            evidence=evidence,
            keywords={"claim", "source", "guidance", "evidence"},
            acceptance=[
                "The target repository records source claims with evidence ids and applicability notes.",
                "The contract names the affected target areas for the first implementation slice.",
                "Out-of-scope claims are recorded with explicit reasons.",
            ],
            risks=_combined_risks(buckets),
        ),
        _spec(
            title=f"Implement source-backed workflow slice for {target.label}",
            reason="The first target change should be the smallest end-to-end behavior supported by source evidence.",
            modules=modules,
            evidence=evidence,
            keywords={"workflow", "entrypoint", "test", "source"},
            acceptance=[
                "The workflow is reachable from the target project entrypoint or primary module.",
                "The implementation records the source claim or artifact that justified the behavior.",
                f"`{target.test_commands[0]}` covers the workflow without external credentials.",
            ],
        ),
        _spec(
            title=f"Add verification evidence for {target.label}",
            reason="The selected Project Version needs reviewable proof for the generated target-project change.",
            modules=[*modules[:2], f"{target.tests_root}/test_evidence.py"],
            evidence=evidence,
            keywords={"test", "review", "evidence", "risk"},
            acceptance=[
                "The target project can persist a verification result containing changed files and test status.",
                "A failed verification includes a blocker reason and recovery action.",
                "Tests cover success and failure evidence records.",
            ],
            priority="medium",
        ),
    ]


def _spec(
    *,
    title: str,
    reason: str,
    modules: list[str],
    evidence: list[SourceEvidence],
    keywords: set[str],
    acceptance: list[str],
    priority: str = "high",
    risks: list[str] | None = None,
) -> CompiledIssueSpec:
    return CompiledIssueSpec(
        title=title,
        reason=reason,
        priority=priority,
        affected_modules=_dedupe(modules),
        acceptance_criteria=acceptance,
        evidence_refs=_evidence_ids(evidence, keywords),
        risks=(risks or ["Keep the issue small enough for one Codex or Claude Code pass."])[:6],
        assumptions=["The selected Project Version target is the local project folder registered in Workbench."],
    )


def _source_summary(title: str, north_star: str, buckets: ArtifactBuckets) -> str:
    parts = [title, north_star]
    for payload in buckets.text_payloads:
        parts.extend(_string_list(payload.get("key_claims")))
        summary = payload.get("summary")
        if isinstance(summary, str):
            parts.append(summary)
    for payload in buckets.repository_payloads:
        parts.extend(_string_list(payload.get("entrypoints")))
        parts.extend(_string_list(payload.get("behavior_patterns")))
        parts.extend(_string_list(payload.get("reusable_patterns")))
        tests = payload.get("tests")
        if isinstance(tests, dict):
            parts.extend(_string_list(tests.get("paths"))[:5])
            parts.extend(_string_list(tests.get("commands"))[:2])
    return "; ".join(part for part in parts if part)[:2200]


def _combined_risks(buckets: ArtifactBuckets) -> list[str]:
    risks: list[str] = []
    for payload in [*buckets.repository_payloads, *buckets.text_payloads]:
        risks.extend(_string_list(payload.get("risks")))
        risks.extend(_string_list(payload.get("limitations")))
        risks.extend(_string_list(payload.get("quality_limitations")))
    return _dedupe(risks) or ["Source reuse must cite evidence and avoid copying reference implementation files."]


def _target_snapshot_phrase(target: TargetShape) -> str:
    if target.selected_files:
        return f"selected files: {', '.join(target.selected_files[:4])}"
    if target.top_level:
        return f"top-level entries: {', '.join(target.top_level[:4])}"
    return "an empty or minimal target checkout"


def _target_modules(target: TargetShape) -> list[str]:
    selected = [item for item in target.selected_files if not item.startswith("tests/")]
    if selected:
        return [*selected[:3], f"{target.tests_root}/test_workflow.py"]
    return [f"{target.source_root}/", f"{target.tests_root}/test_workflow.py"]


def _evidence_ids(evidence: list[SourceEvidence], keywords: set[str]) -> list[str]:
    if not evidence:
        return ["human_goal"]
    scored: list[tuple[int, str]] = []
    for item in evidence:
        text = " ".join([item.claim, item.quote_or_summary, item.locator]).lower()
        score = sum(1 for keyword in keywords if keyword in text)
        scored.append((score, item.id))
    selected = [evidence_id for score, evidence_id in sorted(scored, reverse=True) if score > 0][:5]
    return selected or [item.id for item in evidence[:3]]


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def _dedupe(items: list[str]) -> list[str]:
    deduped: list[str] = []
    for item in items:
        if item and item not in deduped:
            deduped.append(item)
    return deduped


def _package_dir_from_path(value: str) -> str:
    name = Path(value).name if value else "target_project"
    cleaned = "".join(char if char.isalnum() else "_" for char in name.lower()).strip("_")
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned or "target_project"


def _package_dir_from_target(value: str, top_level: list[str], selected_files: list[str]) -> str:
    ignored = {
        ".github",
        ".gitignore",
        "README.md",
        "readme.md",
        "docs",
        "pyproject.toml",
        "requirements.txt",
        "tests",
        "test",
    }
    file_prefixes = {Path(path).parts[0] for path in selected_files if Path(path).parts}
    for item in top_level:
        if item in ignored or "." in item:
            continue
        if item in file_prefixes:
            return _package_dir_from_path(item)
    return _package_dir_from_path(value)


def _mentions_any(text: str, tokens: set[str]) -> bool:
    return any(token in text for token in tokens)


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else f"{text[: limit - 3]}..."
