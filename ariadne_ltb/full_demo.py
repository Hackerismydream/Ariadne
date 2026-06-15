from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ariadne_ltb.board import export_board
from ariadne_ltb.execution import backend_for_name
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.memory import generate_feishu_plan, write_memory_record
from ariadne_ltb.models import (
    AgentRun,
    AgentRunStatus,
    ArtifactType,
    BuildDecision,
    ExecutionContext,
    ExecutionResult,
    FeishuWritePlan,
    MemoryRecord,
    ReviewVerdict,
    TicketStatus,
    stable_id,
)
from ariadne_ltb.review import review_execution
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project, target_test_command


@dataclass(frozen=True)
class FullDemoResult:
    sources_ingested: int
    tickets_created: int
    selected_ticket_id: str
    selected_ticket_key: str
    backend_name: str
    execution_result_id: str
    changed_files: list[str]
    test_exit_code: int | None
    review_verdict: ReviewVerdict
    board_path: Path
    board_html_path: Path
    memory_path: Path
    feishu_plan_path: Path


def default_source_fixtures() -> list[Path]:
    return sorted((Path(__file__).resolve().parents[1] / "examples" / "sources").glob("*.md"))


def run_full_demo(
    root: str | Path = ".",
    source_paths: list[Path] | None = None,
    backend_name: str = "fake-codex",
    confirm_execution: bool = False,
) -> FullDemoResult:
    root_path = Path(root).resolve()
    store = AriadneStore(root_path)
    target_repo = ensure_demo_target_project(root_path)
    sources = source_paths or default_source_fixtures()
    tickets = ingest_sources(store, sources)
    selected = select_code_task_ticket(store, tickets)
    packet = store.load_build_packet(selected.build_packet_id)
    selected = selected.with_status(TicketStatus.READY_FOR_EXECUTION, "Build Lead")
    store.save_ticket(selected)

    execution_run = start_run(store, selected, "Execution", "execution", backend_name)
    context = ExecutionContext(
        ticket_id=selected.id,
        build_packet_id=packet.id,
        target_repo_path=str(target_repo),
        handoff_prompt=handoff_prompt(packet),
        backend_name=backend_name,
        allowed_paths=packet.affected_modules,
        command="Add demo-todo export-json support",
        test_command=target_test_command(),
        confirm_execution=confirm_execution,
        timeout_seconds=60,
    )
    execution = backend_for_name(backend_name).execute(context)
    store.save_execution_result(execution)
    execution_artifacts = write_execution_artifacts(store, execution_run.id, execution)
    execution = execution.model_copy(
        update={
            "execution_log_artifact_id": execution_artifacts["execution_log"],
            "diff_artifact_id": execution_artifacts["git_diff"],
        }
    )
    store.save_execution_result(execution)
    execution_run = finish_run(
        store,
        execution_run,
        "Execution completed.",
        list(execution_artifacts.values()),
    )
    selected = store.load_ticket(selected.id).with_run(execution_run.id).with_artifacts(
        [store.load_artifact(artifact_id) for artifact_id in execution_artifacts.values()]
    ).with_status(TicketStatus.REVIEWING, "Execution")
    selected = selected.model_copy(
        deep=True,
        update={"metadata": selected.metadata | {"execution_result_id": execution.id}},
    )
    store.save_ticket(selected)

    review_run = start_run(store, selected, "Reviewer", "reviewer")
    review = review_execution(store, selected, packet, execution)
    store.save_review_report(review)
    review_artifact = store.write_artifact(
        selected.id,
        review_run.id,
        ArtifactType.REVIEW_REPORT,
        "review_report.json",
        review.model_dump_json(indent=2) + "\n",
        f"Reviewer verdict: {review.verdict.value}",
        metadata={"review_report_id": review.id},
    )
    review_run = finish_run(store, review_run, f"Reviewer verdict: {review.verdict.value}.", [review_artifact.id])
    selected = store.load_ticket(selected.id).with_run(review_run.id).with_artifacts([review_artifact])
    selected = selected.model_copy(
        deep=True,
        update={"metadata": selected.metadata | {"review_report_id": review.id}},
    )
    status = {
        ReviewVerdict.PASS: TicketStatus.WRITING_MEMORY,
        ReviewVerdict.NEEDS_FIX: TicketStatus.NEEDS_FIX,
        ReviewVerdict.BLOCKED: TicketStatus.BLOCKED,
        ReviewVerdict.NEEDS_HUMAN_REVIEW: TicketStatus.WAITING_APPROVAL,
    }[review.verdict]
    selected = selected.with_status(status, "Reviewer")
    store.save_ticket(selected)

    memory_run = start_run(store, selected, "Memory / Feishu", "memory_feishu")
    memory, memory_path = write_memory_record(store, selected, packet, execution, review)
    feishu_plan, feishu_path = generate_feishu_plan(store, selected, packet, execution, review)
    memory_artifact = write_memory_artifact(store, selected.id, memory_run.id, memory, memory_path)
    feishu_artifact = write_feishu_artifact(store, selected.id, memory_run.id, feishu_plan, feishu_path)
    memory_run = finish_run(
        store,
        memory_run,
        "Wrote local memory and Feishu dry-run plan.",
        [memory_artifact.id, feishu_artifact.id],
    )
    final_status = TicketStatus.DONE if review.verdict is ReviewVerdict.PASS else status
    selected = (
        store.load_ticket(selected.id)
        .with_run(memory_run.id)
        .with_artifacts([memory_artifact, feishu_artifact])
        .with_status(final_status, "Memory / Feishu")
    )
    selected = selected.model_copy(
        deep=True,
        update={
            "metadata": selected.metadata
            | {
                "memory_record_id": memory.id,
                "feishu_write_plan_id": feishu_plan.id,
                "selected_for_execution": True,
            }
        },
    )
    store.save_ticket(selected)

    board_path = export_board(store)
    return FullDemoResult(
        sources_ingested=len(sources),
        tickets_created=len(tickets),
        selected_ticket_id=selected.id,
        selected_ticket_key=selected.key,
        backend_name=backend_name,
        execution_result_id=execution.id,
        changed_files=execution.changed_files,
        test_exit_code=execution.test_exit_code,
        review_verdict=review.verdict,
        board_path=board_path,
        board_html_path=store.board_dir / "index.html",
        memory_path=memory_path,
        feishu_plan_path=feishu_path,
    )


def select_code_task_ticket(store: AriadneStore, tickets: list) -> object:
    for ticket in tickets:
        packet = store.load_build_packet(ticket.build_packet_id)
        if packet.build_decision is BuildDecision.CODE_TASK:
            return ticket
    msg = "no code_task ticket found"
    raise RuntimeError(msg)


def handoff_prompt(packet) -> str:
    criteria = "\n".join(f"- {criterion}" for criterion in packet.acceptance_criteria)
    return f"""# Coding Handoff

Goal: {packet.tasks[0]}

Project relevance: {packet.project_relevance}

Allowed paths:
{chr(10).join(f"- {path}" for path in packet.affected_modules)}

Acceptance criteria:
{criteria}
"""


def start_run(
    store: AriadneStore,
    ticket,
    agent_name: str,
    agent_role: str,
    backend_name: str | None = None,
) -> AgentRun:
    attempt = 1 + sum(
        1 for run_id in ticket.agent_run_ids if store.load_run(run_id).agent_role == agent_role
    )
    run = AgentRun(
        id=stable_id("run", ticket.id, agent_role, attempt),
        ticket_id=ticket.id,
        agent_name=agent_name,
        agent_role=agent_role,
        input_summary=f"{agent_name} for {ticket.key}.",
        attempt=attempt,
        backend_name=backend_name,
    ).mark_running()
    store.save_run(run)
    updated = ticket.with_run(run.id).append_event(
        "agent_run_started",
        agent_name,
        f"{agent_name} started.",
        payload_ref=run.id,
    )
    store.save_ticket(updated)
    return run


def finish_run(store: AriadneStore, run: AgentRun, summary: str, artifact_ids: list[str]) -> AgentRun:
    finished = run.model_copy(update={"artifact_ids": artifact_ids}).mark_finished(
        AgentRunStatus.SUCCEEDED,
        summary,
    )
    store.save_run(finished)
    return finished


def write_execution_artifacts(
    store: AriadneStore,
    run_id: str,
    execution: ExecutionResult,
) -> dict[str, str]:
    log = store.write_artifact(
        execution.ticket_id,
        run_id,
        ArtifactType.EXECUTION_LOG,
        "execution_log.json",
        execution.model_dump_json(indent=2) + "\n",
        "Execution stdout/stderr/exit code capture",
        metadata={"execution_result_id": execution.id},
    )
    diff = store.write_artifact(
        execution.ticket_id,
        run_id,
        ArtifactType.GIT_DIFF,
        "git_diff.patch",
        execution.git_diff or "",
        "Target project git diff",
        metadata={"execution_result_id": execution.id},
    )
    changed = store.write_artifact(
        execution.ticket_id,
        run_id,
        ArtifactType.CHANGED_FILES,
        "changed_files.json",
        __import__("json").dumps(execution.changed_files, indent=2) + "\n",
        "Changed file list",
        metadata={"execution_result_id": execution.id},
    )
    tests = store.write_artifact(
        execution.ticket_id,
        run_id,
        ArtifactType.TEST_OUTPUT,
        "test_output.json",
        __import__("json").dumps(
            {
                "test_command": execution.test_command,
                "test_exit_code": execution.test_exit_code,
                "test_stdout": execution.test_stdout,
                "test_stderr": execution.test_stderr,
            },
            indent=2,
        )
        + "\n",
        "Target project test output",
        metadata={"execution_result_id": execution.id},
    )
    return {
        "execution_log": log.id,
        "git_diff": diff.id,
        "changed_files": changed.id,
        "test_output": tests.id,
    }


def write_memory_artifact(store: AriadneStore, ticket_id: str, run_id: str, memory: MemoryRecord, path: Path):
    return store.write_artifact(
        ticket_id,
        run_id,
        ArtifactType.MEMORY_RECORD,
        "memory_record.json",
        memory.model_dump_json(indent=2) + "\n",
        "Local memory write-back record",
        metadata={"memory_record_id": memory.id, "memory_path": str(path)},
    )


def write_feishu_artifact(
    store: AriadneStore,
    ticket_id: str,
    run_id: str,
    plan: FeishuWritePlan,
    path: Path,
):
    return store.write_artifact(
        ticket_id,
        run_id,
        ArtifactType.FEISHU_WRITE_PLAN,
        "feishu_write_plan.json",
        plan.model_dump_json(indent=2) + "\n",
        "Feishu dry-run write plan",
        metadata={"feishu_write_plan_id": plan.id, "path": str(path), "dry_run": True},
    )
