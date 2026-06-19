from __future__ import annotations

from dataclasses import dataclass, field
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


def compile_issue_specs(
    store: AriadneStore,
    *,
    title: str,
    north_star: str,
    context: IssueFactoryContext,
) -> list[CompiledIssueSpec]:
    artifact_payloads = [(artifact, store.load_source_artifact_payload(artifact.id)) for artifact in context.artifacts]
    if _is_mini_code_context(title, north_star, artifact_payloads):
        return _compile_mini_code_agent_specs(context.evidence, artifact_payloads)
    return _compile_generic_specs(title, context.evidence, artifact_payloads)


def _is_mini_code_context(
    title: str,
    north_star: str,
    artifact_payloads: list[tuple[SourceArtifact, dict[str, Any]]],
) -> bool:
    haystack = " ".join([title, north_star, *[str(payload)[:2000] for _, payload in artifact_payloads]]).lower()
    return any(token in haystack for token in ["mini code", "mini-code", "mini-swe", "minimal agent", "code agent", "coding assistant"])


def _evidence_ids(evidence: list[SourceEvidence]) -> list[str]:
    return [item.id for item in evidence] or ["human_goal"]


def _repo_capability_text(artifact_payloads: list[tuple[SourceArtifact, dict[str, Any]]]) -> str:
    parts: list[str] = []
    for _, payload in artifact_payloads:
        parts.extend(str(item) for item in payload.get("behavior_patterns", []))
        parts.extend(str(item) for item in payload.get("entrypoints", []))
        tests = payload.get("tests") or {}
        if isinstance(tests, dict):
            parts.extend(str(item) for item in tests.get("paths", []))
    return "; ".join(parts)[:600]


def _spec(
    title: str,
    reason: str,
    modules: list[str],
    evidence: list[SourceEvidence],
    priority: str = "high",
) -> CompiledIssueSpec:
    return CompiledIssueSpec(
        title=title,
        reason=reason,
        priority=priority,
        affected_modules=modules,
        acceptance_criteria=[
            "The implementation is reachable from the Web Workbench product path.",
            "The behavior writes inspectable run evidence.",
            "Tests cover the behavior without external credentials.",
        ],
        evidence_refs=_evidence_ids(evidence),
        risks=["Keep the issue small enough for one Codex or Claude Code pass."],
        assumptions=["The target project is managed from Ariadne as a local project folder."],
    )


def _compile_mini_code_agent_specs(
    evidence: list[SourceEvidence],
    artifact_payloads: list[tuple[SourceArtifact, dict[str, Any]]],
) -> list[CompiledIssueSpec]:
    capability_text = _repo_capability_text(artifact_payloads) or "reference sources describe compact code-agent loops"
    return [
        _spec("Bootstrap Python package and CLI", f"Reference inputs indicate a CLI-first agent shape: {capability_text}", ["pyproject.toml", "mini_code_agent/__main__.py", "mini_code_agent/cli.py", "tests/test_cli.py"], evidence),
        _spec("Add DeepSeek-backed LLM client configuration", "The target agent needs a real upstream model client and local configuration path.", ["mini_code_agent/llm.py", "mini_code_agent/config.py", "tests/test_llm_config.py"], evidence),
        _spec("Define tool protocol and model action schema", "Reference code-agent projects converge on typed action and observation contracts.", ["mini_code_agent/protocol.py", "tests/test_protocol.py"], evidence),
        _spec("Implement shell command tool with allowlist", "Coding agents need shell access bounded by an explicit local safety policy.", ["mini_code_agent/tools/shell.py", "tests/test_shell_tool.py"], evidence),
        _spec("Implement file read and patch tools with review-before-write safety", "A useful code agent needs file operations without uncontrolled writes.", ["mini_code_agent/tools/files.py", "tests/test_file_tools.py"], evidence),
        _spec("Implement agent loop: prompt -> action -> observation -> repeat", "The core agent behavior is the action/observation loop extracted from references.", ["mini_code_agent/agent_loop.py", "tests/test_agent_loop.py"], evidence),
        _spec("Persist session trace and run summary", "AI Builders need inspectable trajectories to debug agent behavior.", ["mini_code_agent/trace.py", "tests/test_trace.py"], evidence, "medium"),
        _spec("Capture git diff and test result", "A code agent run is not reviewable unless it records diff and tests.", ["mini_code_agent/evidence.py", "tests/test_evidence.py"], evidence),
        _spec("Add minimal reviewer checks for task completion", "A conservative reviewer pass is needed before a run is usable.", ["mini_code_agent/reviewer.py", "tests/test_reviewer.py"], evidence, "medium"),
        _spec("Write README quickstart and usage examples", "The first version needs a runnable local quickstart.", ["README.md", "docs/quickstart.md"], evidence, "medium"),
    ]


def _compile_generic_specs(
    title: str,
    evidence: list[SourceEvidence],
    artifact_payloads: list[tuple[SourceArtifact, dict[str, Any]]],
) -> list[CompiledIssueSpec]:
    modules = _target_modules_from_artifacts(artifact_payloads)
    return [
        _spec(f"Define product contract for {title}", "Compile the goal and selected sources into a concrete implementation contract.", ["docs/product/contract.md"], evidence),
        _spec(f"Implement first vertical slice for {title}", "Build the smallest end-to-end version supported by the source evidence.", modules or ["src/", "tests/"], evidence),
        _spec(f"Add run evidence and review loop for {title}", "Record diff, tests, review verdict, and next issue suggestions for future iterations.", ["src/evidence", "tests/"], evidence, "medium"),
    ]


def _target_modules_from_artifacts(artifact_payloads: list[tuple[SourceArtifact, dict[str, Any]]]) -> list[str]:
    modules: list[str] = []
    for _, payload in artifact_payloads:
        repo_map = payload.get("repo_map") or {}
        if isinstance(repo_map, dict):
            modules.extend(str(item) for item in repo_map.get("selected_files", [])[:6])
    return modules
