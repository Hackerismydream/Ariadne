from __future__ import annotations

import subprocess
from hashlib import sha256
from pathlib import Path

from ariadne_ltb.application.agent_workflow_projection import build_agent_workflows
from ariadne_ltb.application.dtos import CreateProjectVersionInput
from ariadne_ltb.application.issue_projection import build_issue_projection
from ariadne_ltb.application.project_inputs import build_project_inputs
from ariadne_ltb.application.project_version_delivery import build_current_version_delivery
from ariadne_ltb.application.project_versions import ProjectVersionService
from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.application.workbench_environment import build_workbench_environment
from ariadne_ltb.models import (
    AssignmentStatus,
    BuildTicket,
    ExecutionResult,
    FailureReason,
    ReviewReport,
    ReviewVerdict,
    SourceDocument,
    SourceType,
    TicketStatus,
    stable_id,
)
from ariadne_ltb.storage import AriadneStore


def test_project_version_delivery_marks_real_codex_closure(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path / "store")
    target = tmp_path / "target"
    target.mkdir()
    subprocess.run(["git", "init"], cwd=target, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    project = TargetProjectRegistry(store).register(
        target,
        "Mini Code Agent",
        target_project_id="target-mini-code-agent",
        test_command="python3.11 -m pytest",
        issue_prefix="MCA",
    )
    _select_project_version(store, project.id)
    source = _source(store)
    from ariadne_ltb.application.source_analysis import SourceAnalysisService

    SourceAnalysisService(store).analyze_source(source.id)
    ticket = _ticket(project.id, status=TicketStatus.DONE)
    store.save_ticket(ticket)
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("codex"), backend_name="codex")
    assignment = assignment.model_copy(
        update={
            "status": AssignmentStatus.DONE,
            "metadata": assignment.metadata | {"target_project_id": project.id, "target_repo_path": str(target)},
        }
    )
    store.save_assignment(assignment)
    execution = ExecutionResult(
        id="exec-real-codex",
        ticket_id=ticket.id,
        assignment_id=assignment.id,
        backend_name="codex",
        target_repo_path=str(target),
        dry_run=False,
        blocked=False,
        command="codex exec --cd target --prompt-file handoff.md",
        exit_code=0,
        changed_files=["mini_code_agent/cli.py"],
        test_command="python3.11 -m pytest",
        test_exit_code=0,
        handoff_file=".ariadne/handoffs/MCA-001.md",
    )
    store.save_execution_result(execution)
    review = ReviewReport(id="review-real-codex", ticket_id=ticket.id, verdict=ReviewVerdict.PASS)
    store.save_review_report(review)
    store.save_ticket(
        ticket.model_copy(
            update={
                "metadata": ticket.metadata
                | {
                    "latest_assignment_id": assignment.id,
                    "execution_result_id": execution.id,
                    "review_report_id": review.id,
                    "target_project_id": project.id,
                }
            }
        )
    )

    delivery = build_current_version_delivery(store)

    assert delivery is not None
    assert delivery.status == "real_closed"
    assert delivery.latest_real_run is not None
    assert delivery.latest_real_run.backend_name == "codex"
    assert delivery.latest_real_run.dry_run is False
    assert delivery.latest_real_run.changed_files == ["mini_code_agent/cli.py"]
    assert {gate.id: gate.status for gate in delivery.gates}["real_execution"] == "done"
    assert {gate.id: gate.status for gate in delivery.gates}["review"] == "done"


def test_project_version_delivery_does_not_close_blocked_real_codex_run(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path / "store")
    target = tmp_path / "target"
    target.mkdir()
    project = TargetProjectRegistry(store).register(
        target,
        "Mini Code Agent",
        target_project_id="target-mini-code-agent",
        issue_prefix="MCA",
    )
    _select_project_version(store, project.id)
    ticket = _ticket(project.id)
    store.save_ticket(ticket)
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("codex"), backend_name="codex")
    store.save_assignment(assignment.mark_done())
    execution = ExecutionResult(
        id="exec-real-codex-blocked",
        ticket_id=ticket.id,
        assignment_id=assignment.id,
        backend_name="codex",
        target_repo_path=str(target),
        dry_run=False,
        blocked=True,
        block_reason="Codex CLI unavailable",
        failure_reason=FailureReason.EXTERNAL_EXECUTION_BLOCKED,
        command="codex exec",
        exit_code=1,
        changed_files=["README.md"],
        test_command="python3.11 -m pytest",
        test_exit_code=None,
    )
    store.save_execution_result(execution)
    store.save_ticket(
        ticket.model_copy(
            update={
                "metadata": ticket.metadata
                | {
                    "latest_assignment_id": assignment.id,
                    "execution_result_id": execution.id,
                    "target_project_id": project.id,
                }
            }
        )
    )

    delivery = build_current_version_delivery(store)

    assert delivery is not None
    assert delivery.status == "blocked"
    assert delivery.latest_real_run is not None
    assert delivery.latest_real_run.terminal_verdict == "blocked_before_execution"
    assert delivery.latest_real_run.changed_files == []
    gates = {gate.id: gate for gate in delivery.gates}
    assert gates["real_execution"].status == "blocked"
    assert "blocked_before_execution" in gates["real_execution"].detail


def test_project_version_delivery_marks_blocked_assignment_without_execution(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path / "store")
    target = tmp_path / "target"
    target.mkdir()
    project = TargetProjectRegistry(store).register(target, "Mini Code Agent", target_project_id="target")
    _select_project_version(store, project.id)
    ticket = _ticket(project.id)
    store.save_ticket(ticket)
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("codex"), backend_name="codex")
    store.save_assignment(assignment.mark_blocked("handoff missing", FailureReason.UNKNOWN))

    delivery = build_current_version_delivery(store)

    assert delivery is not None
    assert delivery.status == "blocked"
    assert delivery.delivery_items[0].evidence_status == "blocked_before_execution"
    assert delivery.delivery_items[0].terminal_verdict == "blocked_before_execution"
    gates = {gate.id: gate for gate in delivery.gates}
    assert gates["assignment"].status == "blocked"
    assert gates["assignment"].ref_id == assignment.id


def test_project_version_delivery_separates_dirty_base_from_agent_changes(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path / "store")
    target = tmp_path / "target"
    target.mkdir()
    project = TargetProjectRegistry(store).register(target, "Mini Code Agent", target_project_id="target")
    _select_project_version(store, project.id)
    ticket = _ticket(project.id)
    store.save_ticket(ticket)
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("codex"), backend_name="codex")
    store.save_assignment(assignment.mark_done())
    execution = ExecutionResult(
        id="exec-dirty-base",
        ticket_id=ticket.id,
        assignment_id=assignment.id,
        backend_name="codex",
        target_repo_path=str(target),
        dry_run=False,
        blocked=True,
        block_reason="base checkout is dirty",
        failure_reason=FailureReason.DIRTY_BASE_CHECKOUT,
        command="codex exec",
        exit_code=1,
        git_status_before=" M README.md\n?? scratch.py\n",
        changed_files=["README.md", "scratch.py"],
    )
    store.save_execution_result(execution)
    store.save_ticket(ticket.model_copy(update={"metadata": ticket.metadata | {"execution_result_id": execution.id}}))

    delivery = build_current_version_delivery(store)

    assert delivery is not None
    item = delivery.delivery_items[0]
    assert item.changed_files == []
    assert item.preflight_dirty_files == ["README.md", "scratch.py"]


def test_project_version_delivery_uses_selected_project_version_target_project(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path / "store")
    older_target = tmp_path / "older"
    newer_target = tmp_path / "newer"
    older_target.mkdir()
    newer_target.mkdir()
    older_project = TargetProjectRegistry(store).register(
        older_target,
        "Older Project",
        target_project_id="target-older",
        issue_prefix="OLD",
    )
    newer_project = TargetProjectRegistry(store).register(
        newer_target,
        "Mini Code Agent",
        target_project_id="target-newer",
        issue_prefix="MCA",
    )
    ProjectVersionService(store).create(
        CreateProjectVersionInput(
            target_project_id=older_project.id,
            version_label="v0.1",
            goal_title="Older goal",
            goal_north_star="Do not show this project as current.",
        )
    )
    ProjectVersionService(store).create(
        CreateProjectVersionInput(
            target_project_id=newer_project.id,
            version_label="v0.1",
            goal_title="Build Mini Code Agent v0.1",
            goal_north_star="Show this project as current.",
        )
    )
    store.save_ticket(_ticket(older_project.id, key="OLD-001", title="Old task"))
    store.save_ticket(_ticket(newer_project.id, key="MCA-001", title="Current task"))

    delivery = build_current_version_delivery(store)

    assert delivery is not None
    assert delivery.target_project_id == newer_project.id
    assert delivery.target_project_label == "Mini Code Agent"
    assert [item.ticket_key for item in delivery.delivery_items] == ["MCA-001"]


def test_issue_projection_separates_mainline_repairs_and_history(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    main = _ticket("target", key="MCA-001", title="Implement CLI", status=TicketStatus.READY_FOR_EXECUTION)
    repair = _ticket(
        "target",
        key="MCA-011",
        title="Repair MCA-001 reviewer failure",
        metadata={"issue_class": "repair", "root_ticket_key": "MCA-001", "origin": "review"},
    )
    history = _ticket(
        "target",
        key="MCA-012",
        title="Superseded CLI sketch",
        status=TicketStatus.SUPERSEDED,
        metadata={"issue_class": "history", "root_ticket_key": "MCA-001", "origin": "superseded"},
    )
    for ticket in [main, repair, history]:
        store.save_ticket(ticket)

    projection = build_issue_projection(store)

    assert projection.summary["total"] == 3
    family = projection.mainline_tickets[0]
    assert family.ticket_key == "MCA-001"
    assert family.repair_count == 1
    assert family.open_repair_count == 1
    assert family.history_count == 1
    assert {item.ticket_key for item in projection.repair_items} == {"MCA-011"}
    assert {item.ticket_key for item in projection.history_items} == {"MCA-012"}


def test_project_inputs_environment_and_agent_workflow_read_models(tmp_path: Path, monkeypatch) -> None:
    store = AriadneStore(tmp_path / "store")
    target = tmp_path / "target"
    target.mkdir()
    project = TargetProjectRegistry(store).register(target, "Mini Code Agent", target_project_id="target")
    _select_project_version(store, project.id)
    source = _source(store)
    from ariadne_ltb.application.source_analysis import SourceAnalysisService

    SourceAnalysisService(store).analyze_source(source.id)
    ticket = _ticket(project.id)
    store.save_ticket(ticket)
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("codex"), backend_name="codex")
    assignment = assignment.model_copy(update={"metadata": assignment.metadata | {"target_project_id": project.id}})
    store.save_assignment(assignment)

    monkeypatch.setenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", "1")
    inputs = build_project_inputs(store)
    environment = build_workbench_environment(store)
    workflows, activities = build_agent_workflows(store)

    assert inputs
    assert inputs[0].lifecycle.ready_for_issue_factory is True
    assert inputs[0].artifacts
    assert environment.active_target_project_id == project.id
    assert environment.execution_mode in {"real_api_ready", "api_runtime_unavailable"}
    assert workflows
    assert any(step.ticket_key == "MCA-001" and step.agent_name in {"Build Lead", "Runtime", "Codex"} for step in workflows)
    assert isinstance(activities, list)


def _select_project_version(store: AriadneStore, target_project_id: str, *, version_label: str = "v0.1") -> None:
    ProjectVersionService(store).create(
        CreateProjectVersionInput(
            target_project_id=target_project_id,
            version_label=version_label,
            goal_title=f"Mini Code Agent {version_label}",
            goal_north_star="Deliver the selected target project version.",
        )
    )


def _source(store: AriadneStore) -> SourceDocument:
    content = "Mini code agent should expose trajectory, diff, tests, and review evidence."
    source = SourceDocument(
        id=stable_id("source", "note", sha256(content.encode("utf-8")).hexdigest()),
        source_type=SourceType.NOTE,
        title="Mini Code Agent source note",
        path_or_url="file://mini-code-agent.md",
        content_hash=sha256(content.encode("utf-8")).hexdigest(),
        summary=content,
        metadata={"content": content, "source_role": "requirement_source"},
    )
    store.save_source_document(source)
    return source


def _ticket(
    target_project_id: str,
    *,
    key: str = "MCA-001",
    title: str = "Build Mini Code Agent CLI",
    status: TicketStatus = TicketStatus.READY_FOR_EXECUTION,
    metadata: dict[str, object] | None = None,
) -> BuildTicket:
    return BuildTicket(
        id=stable_id("ticket", key),
        key=key,
        title=title,
        description="Build the target project from external source evidence.",
        source_type="issue_factory",
        source_ref=".ariadne/backlog/previews/preview.json",
        status=status,
        priority="high",
        metadata={"target_project_id": target_project_id, "issue_class": "mainline"} | (metadata or {}),
    )
