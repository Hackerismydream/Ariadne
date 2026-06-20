from __future__ import annotations

import subprocess
from hashlib import sha256
from pathlib import Path

from ariadne_ltb.application.agent_workflow_projection import build_agent_workflows
from ariadne_ltb.application.issue_projection import build_issue_projection
from ariadne_ltb.application.project_inputs import build_project_inputs
from ariadne_ltb.application.project_version_delivery import build_current_version_delivery
from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.application.workbench_environment import build_workbench_environment
from ariadne_ltb.models import (
    AssignmentStatus,
    BuildTicket,
    ExecutionResult,
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
