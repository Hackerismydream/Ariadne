from __future__ import annotations

from pathlib import Path
from typing import Any

from ariadne_ltb.knowledge.compile_graph import compile_from_knowledge
from ariadne_ltb.knowledge.models import ProjectPurpose, SynthesisTheme
from ariadne_ltb.knowledge.store import ProjectKnowledgeStore
from ariadne_ltb.storage import AriadneStore


class FakeCompileLLM:
    def complete_json(self, prompt: str, schema_name: str) -> dict[str, Any]:
        if schema_name == "IssueDecompositionDrafts":
            return {
                "issues": [
                    _issue("Build loop", "theme_1"),
                    _issue("Add tools", "theme_1"),
                    _issue("Capture evidence", "theme_1"),
                ]
            }
        if schema_name == "GroundedIssueDrafts":
            return {
                "issues": [
                    _issue("Build loop", "theme_1"),
                    _issue("Add tools", "theme_1"),
                    _issue("Capture evidence", "theme_1"),
                ]
            }
        if schema_name == "GoalCoverageScore":
            return {"coverage": 0.9, "reason": "covers signals"}
        raise AssertionError(schema_name)


def test_compile_graph_returns_compiled_issue_specs(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    knowledge = ProjectKnowledgeStore(store, "project_1")
    purpose = knowledge.save_project_purpose(
        ProjectPurpose(
            project_id="project_1",
            title="Mini Code Agent",
            one_line="Build",
            success_signals=["agent loop works"],
        )
    )
    knowledge.save_synthesis_theme(
        SynthesisTheme(
            id="theme_1",
            project_id="project_1",
            label="Agent loop",
            contributing_source_ids=["source_1"],
            claims=["Use action loop"],
            priority_signal="high",
            affected_modules=["mini_code_agent/agent_loop.py"],
            last_updated_cycle="cycle_1",
        )
    )

    specs = compile_from_knowledge(
        store,
        project_id="project_1",
        target_project_id="project_1",
        purpose=purpose,
        llm=FakeCompileLLM(),
    )

    assert [spec.title for spec in specs] == ["Build loop", "Add tools", "Capture evidence"]
    assert all(spec.evidence_refs == ["theme_1"] for spec in specs)
    assert specs[0].priority == "high"


def test_compile_graph_repairs_missing_modules_and_criteria(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    knowledge = ProjectKnowledgeStore(store, "project_1")
    purpose = knowledge.save_project_purpose(
        ProjectPurpose(project_id="project_1", title="Project", one_line="Build")
    )
    knowledge.save_synthesis_theme(
        SynthesisTheme(
            id="theme_1",
            project_id="project_1",
            label="Theme",
            contributing_source_ids=["source_1"],
            claims=["Claim"],
            last_updated_cycle="cycle_1",
        )
    )
    specs = compile_from_knowledge(
        store,
        project_id="project_1",
        target_project_id="project_1",
        purpose=purpose,
        llm=SparseCompileLLM(),
    )

    assert specs[0].affected_modules == ["src/", "tests/"]
    assert len(specs[0].acceptance_criteria) == 2


def test_compile_graph_uses_theme_fallback_when_planning_llm_fails(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    knowledge = ProjectKnowledgeStore(store, "project_1")
    purpose = knowledge.save_project_purpose(
        ProjectPurpose(project_id="project_1", title="Project", one_line="Build")
    )
    for index in range(3):
        knowledge.save_synthesis_theme(
            SynthesisTheme(
                id=f"theme_{index}",
                project_id="project_1",
                label=f"Theme {index}",
                contributing_source_ids=["source_1"],
                claims=[f"Claim {index}"],
                priority_signal="high",
                affected_modules=[f"module_{index}.py"],
                last_updated_cycle="cycle_1",
            )
        )

    specs = compile_from_knowledge(
        store,
        project_id="project_1",
        target_project_id="project_1",
        purpose=purpose,
        llm=FailingPlanLLM(),
    )

    assert [spec.title for spec in specs] == [
        "Implement Theme 0",
        "Implement Theme 1",
        "Implement Theme 2",
    ]
    assert specs[0].evidence_refs == ["theme_0"]


def test_retry_prompt_includes_previous_quality_issues(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    knowledge = ProjectKnowledgeStore(store, "project_1")
    purpose = knowledge.save_project_purpose(
        ProjectPurpose(project_id="project_1", title="Project", one_line="Build")
    )
    knowledge.save_synthesis_theme(
        SynthesisTheme(
            id="theme_1",
            project_id="project_1",
            label="Theme",
            contributing_source_ids=["source_1"],
            claims=["Claim"],
            priority_signal="high",
            affected_modules=["module.py"],
            last_updated_cycle="cycle_1",
        )
    )
    llm = RetryingCompileLLM()

    specs = compile_from_knowledge(
        store,
        project_id="project_1",
        target_project_id="project_1",
        purpose=purpose,
        llm=llm,
    )

    assert len(specs) == 3
    assert "count_out_of_range" in llm.plan_prompts[1]


def _issue(title: str, evidence_ref: str) -> dict[str, Any]:
    return {
        "title": title,
        "reason": f"{title} is needed because source evidence supports it.",
        "priority": "P0",
        "affected_modules": ["mini_code_agent/agent_loop.py"],
        "acceptance_criteria": ["It is reachable from CLI.", "Tests cover it."],
        "evidence_refs": [evidence_ref],
        "depends_on": [],
        "owner_agent": "Build Lead",
        "build_decision": "code_task",
        "risks": [],
        "assumptions": [],
    }


class SparseCompileLLM:
    def complete_json(self, prompt: str, schema_name: str) -> dict[str, Any]:
        if schema_name == "IssueDecompositionDrafts":
            return {
                "issues": [
                    _sparse_issue("One"),
                    _sparse_issue("Two"),
                    _sparse_issue("Three"),
                ]
            }
        if schema_name == "GroundedIssueDrafts":
            return {
                "issues": [
                    _sparse_issue("One"),
                    _sparse_issue("Two"),
                    _sparse_issue("Three"),
                ]
            }
        if schema_name == "GoalCoverageScore":
            return {"coverage": 0.8, "reason": "ok"}
        raise AssertionError(schema_name)


class FailingPlanLLM:
    def complete_json(self, prompt: str, schema_name: str) -> dict[str, Any]:
        if schema_name == "IssueDecompositionDrafts":
            raise ValueError("not json")
        if schema_name == "GroundedIssueDrafts":
            return {
                "issues": [
                    _sparse_issue("Implement Theme 0") | {"evidence_refs": ["theme_0"]},
                    _sparse_issue("Implement Theme 1") | {"evidence_refs": ["theme_1"]},
                    _sparse_issue("Implement Theme 2") | {"evidence_refs": ["theme_2"]},
                ]
            }
        if schema_name == "GoalCoverageScore":
            return {"coverage": 0.8, "reason": "ok"}
        raise AssertionError(schema_name)


class RetryingCompileLLM:
    def __init__(self) -> None:
        self.plan_prompts: list[str] = []

    def complete_json(self, prompt: str, schema_name: str) -> dict[str, Any]:
        if schema_name == "IssueDecompositionDrafts":
            self.plan_prompts.append(prompt)
            if len(self.plan_prompts) == 1:
                return {"issues": [_issue("Too small", "theme_1")]}
            return {
                "issues": [
                    _issue("One", "theme_1"),
                    _issue("Two", "theme_1"),
                    _issue("Three", "theme_1"),
                ]
            }
        if schema_name == "GroundedIssueDrafts":
            return {
                "issues": [
                    _issue("One", "theme_1"),
                    _issue("Two", "theme_1"),
                    _issue("Three", "theme_1"),
                ]
                if len(self.plan_prompts) > 1
                else [_issue("Too small", "theme_1")]
            }
        if schema_name == "GoalCoverageScore":
            return {"coverage": 0.8, "reason": "ok"}
        raise AssertionError(schema_name)


def _sparse_issue(title: str) -> dict[str, Any]:
    return {
        "title": title,
        "reason": "Sparse real LLM output still needs deterministic hardening.",
        "priority": "P1",
        "affected_modules": [],
        "acceptance_criteria": [],
        "evidence_refs": ["theme_1"],
        "depends_on": [],
    }
