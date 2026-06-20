from __future__ import annotations

import subprocess
from hashlib import sha256
from pathlib import Path

import pytest

from ariadne_ltb.application.dtos import CreateProjectGoalInput, IssueFactoryPreviewInput
from ariadne_ltb.application.issue_delta_validation import validate_issue_delta_operation
from ariadne_ltb.application.issue_factory import IssueFactoryService
from ariadne_ltb.application.project_goals import ProjectGoalService
from ariadne_ltb.application.source_analysis import SourceAnalysisService
from ariadne_ltb.models import (
    BacklogOperation,
    BacklogOperationType,
    SourceDocument,
    SourceType,
    TicketStatus,
    stable_id,
)
from ariadne_ltb.storage import AriadneStore


def test_issue_factory_compiles_mca_issue_set_from_typed_artifacts(tmp_path: Path) -> None:
    store, goal_id, project_id, source_ids = _seed_mini_code_agent_context(tmp_path)

    preview = IssueFactoryService(store).preview(
        IssueFactoryPreviewInput(goal_id=goal_id, source_ids=source_ids, target_project_id=project_id)
    )

    keys = [operation.ticket_key for operation in preview.operations]
    titles = [operation.title for operation in preview.operations]

    assert keys[:10] == [
        "MCA-001",
        "MCA-002",
        "MCA-003",
        "MCA-004",
        "MCA-005",
        "MCA-006",
        "MCA-007",
        "MCA-008",
        "MCA-009",
        "MCA-010",
    ]
    assert "Bootstrap Python package and CLI" in titles
    assert "Add DeepSeek-backed LLM client configuration" in titles
    assert "Define tool protocol and model action schema" in titles
    assert "Implement shell command tool with allowlist" in titles
    assert "Implement file read and patch tools with review-before-write safety" in titles
    assert "Implement agent loop: prompt -> action -> observation -> repeat" in titles
    assert "Persist session trace and run summary" in titles
    assert "Capture git diff and test result" in titles
    assert "Add minimal reviewer checks for task completion" in titles
    assert "Write README quickstart and usage examples" in titles
    bootstrap = next(operation for operation in preview.operations if operation.ticket_key == "MCA-001")
    assert ".mini-code-agent/" in bootstrap.metadata["affected_modules"]

    for operation in preview.operations:
        assert operation.metadata["target_project_id"] == project_id
        assert operation.metadata["build_context_id"]
        assert operation.metadata["context_fingerprint"]
        assert operation.metadata["source_document_ids"]
        assert operation.metadata["source_artifact_ids"]
        assert operation.metadata["evidence_refs"]
        assert operation.metadata["affected_modules"]
        assert operation.metadata["acceptance_criteria"]
        assert operation.metadata["goal_reason"]


def test_issue_factory_rejects_unanalyzed_source(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path / "store")
    target = tmp_path / "target"
    target.mkdir()
    project_id = "target_1"
    store.save_project_resources(
        [
            store_project_resource(
                project_id=project_id,
                path=target,
                label="Target",
                issue_prefix="TGT",
                test_command="python3.11 -m pytest",
            )
        ]
    )
    goal = ProjectGoalService(store).create(
        CreateProjectGoalInput(
            title="Build Target",
            north_star="Use sources to create issues.",
            target_project_id=project_id,
        )
    )
    source_id = _create_source(
        store,
        SourceType.NOTE,
        "unread source",
        "memory://unread",
        "This source has not been analyzed.",
        {"source_role": "requirement_source"},
    )

    with pytest.raises(ValueError, match="source_not_ready_for_issue_factory"):
        IssueFactoryService(store).preview(
            IssueFactoryPreviewInput(goal_id=goal.id, source_ids=[source_id], target_project_id=project_id)
        )


def test_issue_factory_uses_artifact_payload_not_only_title(tmp_path: Path) -> None:
    store, goal_id, project_id, source_ids = _seed_mini_code_agent_context(tmp_path)
    source = store.load_source_document(source_ids[1])
    artifacts = store.list_source_artifacts(source.id)
    payload = store.load_source_artifact_payload(artifacts[0].id)
    assert "tests" in payload

    preview = IssueFactoryService(store).preview(
        IssueFactoryPreviewInput(goal_id=goal_id, source_ids=source_ids, target_project_id=project_id)
    )

    loop_issue = next(operation for operation in preview.operations if "agent loop" in (operation.title or "").lower())
    assert artifacts[0].id in loop_issue.metadata["source_artifact_ids"]
    assert loop_issue.metadata["evidence_refs"]
    assert "mini_code_agent/agent_loop.py" in loop_issue.metadata["affected_modules"]


def test_issue_factory_updates_existing_target_issue_scope(tmp_path: Path) -> None:
    store, goal_id, project_id, source_ids = _seed_mini_code_agent_context(tmp_path)
    service = IssueFactoryService(store)
    first_preview = service.preview(
        IssueFactoryPreviewInput(goal_id=goal_id, source_ids=source_ids, target_project_id=project_id)
    )
    service.apply(first_preview.id)
    ticket = store.resolve_ticket("MCA-001")
    old_scope = ["pyproject.toml", "mini_code_agent/__main__.py", "mini_code_agent/cli.py", "tests/test_cli.py"]
    store.save_ticket(ticket.model_copy(deep=True, update={"metadata": ticket.metadata | {"affected_modules": old_scope}}))
    packet = store.load_build_packet(ticket.build_packet_id)
    store.save_build_packet(packet.model_copy(update={"affected_modules": old_scope}))

    update_preview = service.preview(
        IssueFactoryPreviewInput(goal_id=goal_id, source_ids=source_ids, target_project_id=project_id)
    )

    bootstrap = next(operation for operation in update_preview.operations if operation.ticket_key == "MCA-001")
    assert bootstrap.operation_type == "update_ticket"
    assert ".mini-code-agent/" in bootstrap.metadata["affected_modules"]
    service.apply(update_preview.id)
    updated_ticket = store.resolve_ticket("MCA-001")
    updated_packet = store.load_build_packet(updated_ticket.build_packet_id)
    assert ".mini-code-agent/" in updated_ticket.metadata["affected_modules"]
    assert ".mini-code-agent/" in updated_packet.affected_modules


def test_issue_delta_validator_rejects_generic_code_task() -> None:
    operation = BacklogOperation(
        id="op_bad",
        operation_type=BacklogOperationType.ADD_TICKET,
        ticket_id="ticket_bad",
        ticket_key="MCA-999",
        title="Implement stuff",
        description="Do useful implementation work.",
        source_type="note",
        source_ref="ariadne://test",
        priority="high",
        status=TicketStatus.PLANNING,
        reason="Too generic",
        metadata={
            "target_project_id": "project_1",
            "build_context_id": "ctx_1",
            "context_fingerprint": "fingerprint_1",
            "source_document_ids": ["source_1"],
            "source_artifact_ids": ["artifact_1"],
            "evidence_refs": ["evidence_1"],
            "affected_modules": ["src/"],
            "acceptance_criteria": ["It works."],
            "goal_reason": "Too generic",
        },
    )

    with pytest.raises(ValueError, match="generic_issue_title"):
        validate_issue_delta_operation(operation)


def _seed_mini_code_agent_context(tmp_path: Path) -> tuple[AriadneStore, str, str, list[str]]:
    store = AriadneStore(tmp_path / "store")
    target = tmp_path / "mini-code-agent"
    target.mkdir()
    subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)
    (target / "README.md").write_text("# mini-code-agent\n", encoding="utf-8")
    project_id = "target_mini_code_agent"
    store.save_project_resources(
        [
            store_project_resource(
                project_id=project_id,
                path=target,
                label="Mini Code Agent",
                issue_prefix="MCA",
                test_command="python3.11 -m pytest",
            )
        ]
    )
    goal = ProjectGoalService(store).create(
        CreateProjectGoalInput(
            title="Build Mini Code Agent",
            north_star="Build a Python mini code agent MVP for local AI Builders.",
            current_state="Empty local project.",
            target_state="Runnable v0.1 with CLI, LLM client, tools, trace, tests, and review.",
            target_project_id=project_id,
        )
    )
    source_ids = [
        _create_source(
            store,
            SourceType.NOTE,
            "minimal-agent blog",
            "https://minimal-agent.com/",
            "Minimal agents loop through query model, parse action, execute action, observe, repeat.",
            {"source_role": "requirement_source"},
        ),
        _create_reference_repo(store, tmp_path / "mini-swe-agent", "mini-SWE-agent"),
        _create_reference_repo(store, tmp_path / "minicode", "MiniCode"),
        _create_source(
            store,
            SourceType.TARGET_CODEBASE,
            "mini-code-agent target",
            str(target),
            "",
            {"source_role": "target_codebase"},
        ),
    ]
    analyzer = SourceAnalysisService(store)
    for source_id in source_ids:
        analyzer.analyze_source(source_id)
    return store, goal.id, project_id, source_ids


def _create_reference_repo(store: AriadneStore, path: Path, title: str) -> str:
    path.mkdir()
    (path / "README.md").write_text(
        f"# {title}\n\nCLI coding assistant with sessions, diff review, and test result capture.",
        encoding="utf-8",
    )
    (path / "LICENSE").write_text("MIT License", encoding="utf-8")
    (path / "pyproject.toml").write_text(
        "[project]\nname='reference'\n[project.scripts]\nreference='reference.cli:main'\n",
        encoding="utf-8",
    )
    (path / "tests").mkdir()
    (path / "tests" / "test_cli.py").write_text("def test_cli():\n    assert True\n", encoding="utf-8")
    return _create_source(
        store,
        SourceType.GITHUB_REPO,
        title,
        str(path),
        "",
        {"source_role": "reference_project"},
    )


def _create_source(
    store: AriadneStore,
    source_type: SourceType,
    title: str,
    path_or_url: str,
    content: str,
    metadata: dict[str, object],
) -> str:
    source = SourceDocument(
        id=stable_id("source", path_or_url, title, sha256(content.encode("utf-8")).hexdigest()),
        source_type=source_type,
        title=title,
        path_or_url=path_or_url,
        content_hash=sha256((path_or_url + "\n" + content).encode("utf-8")).hexdigest(),
        summary=content[:240] or title,
        metadata=metadata | {"content": content},
    )
    store.save_source_document(source)
    return source.id


def store_project_resource(*, project_id: str, path: Path, label: str, issue_prefix: str, test_command: str):
    from ariadne_ltb.models import ProjectResource

    resource = ProjectResource.local_directory(project_id, path, label=label)
    return resource.model_copy(
        update={
            "id": project_id,
            "resource_ref": resource.resource_ref
            | {
                "issue_prefix": issue_prefix,
                "test_command": test_command,
            }
        }
    )
