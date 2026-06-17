from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Annotated

import typer

from ariadne_ltb.board import export_board
from ariadne_ltb.board_server import board_serve_command
from ariadne_ltb.backlog import supersede_ticket
from ariadne_ltb.daemon import LocalDaemonWorker, is_stale_heartbeat
from ariadne_ltb.demo import create_demo_ticket, default_source_path, ensure_project_space, run_demo
from ariadne_ltb.execution import CodexBackend, backend_for_name
from ariadne_ltb.feishu import create_lark_doc_from_plan
from ariadne_ltb.full_demo import default_source_fixtures, run_full_demo, select_code_task_ticket
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.journal import build_resume_plan
from ariadne_ltb.local_safety import clear_stale_locks, list_locks
from ariadne_ltb.memory import generate_feishu_plan, write_memory_record
from ariadne_ltb.models import (
    AssignmentStatus,
    BacklogUpdate,
    CommentAuthorType,
    CommentKind,
    ExecutionContext,
    ResumeSafety,
    TicketComment,
    TicketStatus,
)
from ariadne_ltb.orchestrator import TicketRunOrchestrator
from ariadne_ltb.planner import planner_for_name
from ariadne_ltb.retry import create_retry_assignment
from ariadne_ltb.review import review_execution
from ariadne_ltb.runtime import collect_runtime_capabilities
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project, target_test_command

app = typer.Typer(help="Ariadne local deterministic Learning-to-Build workbench.")
agent_app = typer.Typer(help="Agent teammate commands.")
assignment_app = typer.Typer(help="Assignment queue commands.")
ticket_app = typer.Typer(help="Build Ticket commands.")
export_app = typer.Typer(help="Export commands.")
memory_app = typer.Typer(help="Memory commands.")
backend_app = typer.Typer(help="Execution backend diagnostics and smoke tests.")
daemon_app = typer.Typer(help="Local daemon worker commands.")
runtime_app = typer.Typer(help="Runtime journal and recovery commands.")
run_app = typer.Typer(help="Agent Run message stream commands.")
board_app = typer.Typer(help="Local board commands.")
doctor_app = typer.Typer(help="Release and safety doctors.")
backlog_app = typer.Typer(help="Ticket backlog update commands.")
app.add_typer(agent_app, name="agent")
app.add_typer(assignment_app, name="assignment")
app.add_typer(ticket_app, name="ticket")
app.add_typer(export_app, name="export")
app.add_typer(memory_app, name="memory")
app.add_typer(backend_app, name="backend")
app.add_typer(daemon_app, name="daemon")
app.add_typer(runtime_app, name="runtime")
app.add_typer(run_app, name="run")
app.add_typer(board_app, name="board")
app.add_typer(doctor_app, name="doctor")
app.add_typer(backlog_app, name="backlog")


class CliState:
    root: Path = Path(".")


state = CliState()


@app.callback()
def configure(
    root: Annotated[
        Path,
        typer.Option("--root", help="Project root containing the .ariadne workspace."),
    ] = Path("."),
) -> None:
    state.root = root.resolve()


@app.command()
def demo(
    mode: Annotated[str, typer.Argument(help="Demo mode: `kernel` or `full`.")] = "kernel",
    backend: Annotated[str, typer.Option("--backend", help="Execution backend.")] = "fake-codex",
    confirm_execution: Annotated[
        bool,
        typer.Option("--confirm-execution", help="Allow non-dry-run external execution backends."),
    ] = False,
) -> None:
    """Run the Ariadne demo pipeline."""
    if mode == "full":
        result = run_full_demo(
            root=state.root,
            source_paths=default_source_fixtures(),
            backend_name=backend,
            confirm_execution=confirm_execution,
        )
        typer.echo(f"sources ingested: {result.sources_ingested}")
        typer.echo(f"tickets created: {result.tickets_created}")
        typer.echo(f"selected ticket: {result.selected_ticket_key} ({result.selected_ticket_id})")
        typer.echo(f"backend used: {result.backend_name}")
        typer.echo(f"changed files: {', '.join(result.changed_files)}")
        typer.echo(f"test exit code: {result.test_exit_code}")
        typer.echo(f"reviewer verdict: {result.review_verdict.value}")
        typer.echo(f"board: {result.board_path}")
        typer.echo(f"memory: {result.memory_path}")
        typer.echo(f"feishu plan: {result.feishu_plan_path}")
        typer.echo(f"next tickets: {result.next_tickets_path}")
        return
    if mode != "kernel":
        raise typer.BadParameter("mode must be `kernel` or `full`")
    result = run_demo(root=state.root)
    typer.echo(f"Created and ran {result.ticket_key} ({result.ticket_id})")
    typer.echo(f"Artifacts: {result.artifacts_dir}")
    typer.echo(f"Board: {result.board_path}")


@app.command()
def ingest(
    paths: list[Path],
    planner: Annotated[
        str | None,
        typer.Option("--planner", help="Optional planner to run after ingest: deterministic|llm."),
    ] = None,
) -> None:
    """Ingest local markdown sources into Build Tickets and Build Packets."""
    store = AriadneStore(state.root)
    tickets = ingest_sources(store, paths)
    if planner:
        planner_backend = planner_for_name(planner)
        for ticket in tickets:
            planner_backend.plan_ticket(store, ticket)
    typer.echo(f"Ingested {len(tickets)} source(s)")
    for ticket in tickets:
        typer.echo(f"{ticket.key} {ticket.source_type} {ticket.title}")


@backlog_app.command("update")
def backlog_update(
    source_paths: Annotated[
        list[Path] | None,
        typer.Argument(help="Additional source paths, useful for shell-expanded globs."),
    ] = None,
    from_sources: Annotated[
        list[Path] | None,
        typer.Option("--from-source", help="Source markdown path to ingest into the ticket backlog."),
    ] = None,
) -> None:
    """Update the ticket backlog from local source documents."""
    paths = [*(from_sources or []), *(source_paths or [])]
    if not paths:
        typer.echo("No --from-source paths provided.")
        raise typer.Exit(2)
    store = AriadneStore(state.root)
    try:
        tickets = ingest_sources(store, paths)
    except OSError as exc:
        typer.echo(str(exc))
        raise typer.Exit(2) from exc
    update = store.list_backlog_updates()[-1]
    typer.echo(f"backlog update: {update.id}")
    typer.echo(f"trigger: {update.trigger_type.value}")
    typer.echo(f"created tickets: {len(update.created_ticket_ids)}")
    typer.echo(f"updated tickets: {len(update.updated_ticket_ids)}")
    typer.echo(f"superseded tickets: {len(update.superseded_ticket_ids)}")
    typer.echo(f"ticket changes: {len(update.ticket_changes)}")
    typer.echo(f"rationale: {update.rationale}")
    for ticket in tickets:
        typer.echo(f"{ticket.key}\t{ticket.status.value}\t{ticket.title}")


@backlog_app.command("history")
def backlog_history(limit: Annotated[int, typer.Option("--limit")] = 20) -> None:
    """Show recent ticket backlog updates."""
    if limit < 1:
        typer.echo("--limit must be greater than 0.")
        raise typer.Exit(2)
    updates = AriadneStore(state.root).list_backlog_updates()[-limit:]
    if not updates:
        typer.echo("No backlog updates.")
        return
    for update in updates:
        typer.echo(f"{update.created_at}\t{update.id}\t{update.trigger_type.value}")
        typer.echo(f"rationale: {update.rationale}")
        typer.echo(
            "tickets: "
            f"created={len(update.created_ticket_ids)} "
            f"updated={len(update.updated_ticket_ids)} "
            f"superseded={len(update.superseded_ticket_ids)} "
            f"changes={_ticket_change_counts(update)}"
        )
        for change in update.ticket_changes:
            typer.echo(
                f"- {change.ticket_key}\t{change.change_type.value}\t"
                f"{change.before_status or ''}->{change.after_status or ''}\t{change.reason}"
            )
        if update.evidence_refs:
            typer.echo(f"evidence: {', '.join(update.evidence_refs)}")


def _ticket_change_counts(update: BacklogUpdate) -> str:
    counts: dict[str, int] = {}
    for change in update.ticket_changes:
        counts[change.change_type.value] = counts.get(change.change_type.value, 0) + 1
    return ",".join(f"{key}:{counts[key]}" for key in sorted(counts)) or "none"


@agent_app.command("list")
def agent_list() -> None:
    """List local Ariadne Agent teammates."""
    store = AriadneStore(state.root)
    for profile in store.ensure_default_agent_profiles():
        capabilities = ",".join(profile.capabilities)
        typer.echo(
            f"{profile.id}\t{profile.name}\t{profile.role}\t"
            f"{profile.backend_name or ''}\t{profile.enabled}\t{capabilities}"
        )


@assignment_app.command("list")
def assignment_list() -> None:
    """List Ticket assignments."""
    store = AriadneStore(state.root)
    assignments = store.list_assignments()
    if not assignments:
        typer.echo("No assignments.")
        return
    for assignment in assignments:
        typer.echo(
            f"{assignment.id}\t{assignment.ticket_key}\t{assignment.agent_id}\t"
            f"{assignment.status.value}\tattempt={assignment.attempt}\t"
            f"parent={assignment.parent_assignment_id or ''}"
        )


@assignment_app.command("show")
def assignment_show(assignment_id: str) -> None:
    """Show one Ticket assignment."""
    assignment = AriadneStore(state.root).load_assignment(assignment_id)
    typer.echo(f"id: {assignment.id}")
    typer.echo(f"ticket: {assignment.ticket_key}")
    typer.echo(f"agent: {assignment.agent_id}")
    typer.echo(f"status: {assignment.status.value}")
    typer.echo(f"attempt: {assignment.attempt}")
    typer.echo(f"parent: {assignment.parent_assignment_id or ''}")
    typer.echo(f"failure reason: {assignment.failure_reason.value if assignment.failure_reason else ''}")
    typer.echo(f"blocker: {assignment.blocker or ''}")


@assignment_app.command("retry")
def assignment_retry(
    assignment_id: str,
    reason: Annotated[str, typer.Option("--reason")] = "retry requested",
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    """Create a new queued retry assignment from a blocked or failed assignment."""
    store = AriadneStore(state.root)
    try:
        retry = create_retry_assignment(store, store.load_assignment(assignment_id), reason, force)
    except ValueError as exc:
        typer.echo(str(exc))
        raise typer.Exit(2) from exc
    typer.echo(f"retry assignment: {retry.id}")
    typer.echo(f"parent: {retry.parent_assignment_id}")
    typer.echo(f"attempt: {retry.attempt}")


@backend_app.command("doctor")
def backend_doctor() -> None:
    """Report local backend availability and safety-gate state without secrets."""
    store = AriadneStore(state.root)
    store.save_runtime_capabilities(collect_runtime_capabilities())
    codex_path = shutil.which("codex")
    claude_path = shutil.which("claude")
    external_enabled = os.environ.get("ARIADNE_ENABLE_EXTERNAL_EXECUTION") == "1"
    typer.echo("FakeCodexBackend: available")
    typer.echo("ShellBackend: available")
    typer.echo(f"CodexBackend command: {'found ' + codex_path if codex_path else 'missing'}")
    typer.echo(f"ClaudeCodeBackend command: {'found ' + claude_path if claude_path else 'missing'}")
    typer.echo(f"Codex command path: {codex_path or 'missing'}")
    typer.echo(f"Claude command path: {claude_path or 'missing'}")
    typer.echo(
        f"Codex command template set? "
        f"{'yes' if os.environ.get('ARIADNE_CODEX_COMMAND_TEMPLATE') else 'no'}"
    )
    typer.echo(
        f"Claude command template set? "
        f"{'yes' if os.environ.get('ARIADNE_CLAUDE_COMMAND_TEMPLATE') else 'no'}"
    )
    typer.echo(f"External execution enabled? {'yes' if external_enabled else 'no'}")
    typer.echo("Confirm required? yes")
    for variable in [
        "ARIADNE_ENABLE_EXTERNAL_EXECUTION",
        "ARIADNE_CODEX_COMMAND_TEMPLATE",
        "ARIADNE_CLAUDE_COMMAND_TEMPLATE",
        "FEISHU_ENABLE_WRITE",
        "DEEPSEEK_API_KEY",
    ]:
        typer.echo(f"{variable}: {'set' if os.environ.get(variable) else 'unset'}")
    from ariadne_ltb.secret_safety import secret_status_lines

    for line in secret_status_lines(state.root):
        typer.echo(line)


@backend_app.command("smoke-test")
def backend_smoke_test(
    backend: Annotated[str, typer.Argument(help="Backend smoke test target. Only `codex` is supported.")],
    confirm_execution: Annotated[bool, typer.Option("--confirm-execution")] = False,
    timeout_seconds: Annotated[
        int,
        typer.Option("--timeout-seconds", help="Maximum seconds for the real backend command."),
    ] = 300,
) -> None:
    """Run a safety-gated real backend smoke test through TicketRunOrchestrator."""
    if backend != "codex":
        raise typer.BadParameter("only `codex` smoke test is supported")
    if os.environ.get("ARIADNE_ENABLE_EXTERNAL_EXECUTION") != "1":
        typer.echo(
            "Refusing real Codex smoke test: ARIADNE_ENABLE_EXTERNAL_EXECUTION must be 1."
        )
        raise typer.Exit(2)
    if not confirm_execution:
        typer.echo("Refusing real Codex smoke test: --confirm-execution is required.")
        raise typer.Exit(2)
    if not CodexBackend().is_available():
        typer.echo("Refusing real Codex smoke test: codex command is not available.")
        raise typer.Exit(2)

    store = AriadneStore(state.root)
    target_repo = ensure_demo_target_project(state.root)
    tickets = ingest_sources(store, default_source_fixtures())
    selected = select_code_task_ticket(store, tickets)
    result = TicketRunOrchestrator(store).run_ticket(
        selected.key,
        backend_name="codex",
        target_repo_path=str(target_repo),
        confirm_execution=True,
        timeout_seconds=timeout_seconds,
    )
    handoff_file = state.root / ".ariadne" / "handoffs" / f"{result.ticket_key}.md"
    execution = store.load_execution_result(result.execution_result_id)

    typer.echo(f"ticket: {result.ticket_key} ({result.ticket_id})")
    typer.echo(f"backend: {result.backend_name}")
    typer.echo(f"handoff file: {handoff_file}")
    typer.echo(f"execution result: {result.execution_result_id}")
    typer.echo(f"exit code: {execution.exit_code}")
    typer.echo(f"changed files: {', '.join(result.changed_files)}")
    typer.echo(f"test exit code: {result.test_exit_code}")
    typer.echo(f"review verdict: {result.review_verdict}")
    typer.echo(f"board: {result.board_path}")
    typer.echo(f"memory: {result.memory_path}")
    typer.echo(f"feishu dry-run plan: {result.feishu_plan_path}")
    typer.echo(f"next tickets: {result.next_tickets_path}")


@ticket_app.command("create")
def ticket_create(
    source: Annotated[
        Path,
        typer.Option("--source", help="Source research note path."),
    ] = default_source_path(),
) -> None:
    """Create the deterministic demo Build Ticket without running the pipeline."""
    store = AriadneStore(state.root)
    ensure_project_space(store)
    ticket = create_demo_ticket(source.resolve())
    store.save_ticket(ticket)
    typer.echo(f"Created {ticket.key} ({ticket.id})")


@ticket_app.command("show")
def ticket_show(ticket_id: str) -> None:
    """Show a readable Build Ticket summary."""
    store = AriadneStore(state.root)
    ticket = store.resolve_ticket(ticket_id)
    typer.echo(f"{ticket.key}: {ticket.title}")
    typer.echo(f"Status: {ticket.status.value}")
    typer.echo(f"Source: {ticket.source_ref}")
    typer.echo(f"Runs: {len(ticket.agent_run_ids)}")
    typer.echo(f"Artifacts: {len(ticket.artifact_ids)}")
    store = AriadneStore(state.root)
    assignment = store.find_latest_assignment_for_ticket(ticket.id)
    if assignment:
        typer.echo(
            f"Assignment: {assignment.agent_id} {assignment.status.value} "
            f"backend={assignment.backend_name or ''}"
        )


@ticket_app.command("list")
def ticket_list() -> None:
    """List Build Tickets."""
    for ticket in AriadneStore(state.root).list_tickets():
        typer.echo(f"{ticket.key}\t{ticket.status.value}\t{ticket.source_type}\t{ticket.title}")


@ticket_app.command("assign")
def ticket_assign(
    ticket_id: str,
    agent_id: Annotated[str, typer.Option("--to", help="Agent profile id or name.")],
    backend: Annotated[str | None, typer.Option("--backend", help="Override backend name.")] = None,
) -> None:
    """Assign a Build Ticket to a local Agent teammate."""
    store = AriadneStore(state.root)
    ticket = store.resolve_ticket(ticket_id)
    agent = store.resolve_agent_profile(agent_id)
    assignment = store.create_assignment(ticket, agent, backend_name=backend)
    status = (
        TicketStatus.READY_FOR_EXECUTION
        if (assignment.backend_name or agent.backend_name) == "fake-codex"
        else TicketStatus.WAITING_APPROVAL
    )
    updated = store.load_ticket(ticket.id).with_status(
        status,
        "Ariadne",
        f"Assigned to {agent.name}.",
    )
    store.save_ticket(updated)
    typer.echo(f"Assignment created: {assignment.id}")
    typer.echo(f"ticket: {ticket.key}")
    typer.echo(f"agent: {agent.id}")
    typer.echo(f"backend: {assignment.backend_name or ''}")


@ticket_app.command("comment")
def ticket_comment(
    ticket_id: str,
    message: str,
    reply_to: Annotated[str | None, typer.Option("--reply-to", help="Reply to an existing comment id.")] = None,
) -> None:
    """Add a human comment to a Build Ticket."""
    store = AriadneStore(state.root)
    ticket = store.resolve_ticket(ticket_id)
    try:
        comment = store.add_comment(
            ticket,
            CommentAuthorType.HUMAN,
            "human",
            CommentKind.COMMENT,
            message,
            parent_comment_id=reply_to,
        )
    except ValueError as exc:
        typer.echo(str(exc))
        raise typer.Exit(2) from exc
    typer.echo(f"comment: {comment.id}")
    typer.echo(f"thread: {comment.thread_id}")


@ticket_app.command("comments")
def ticket_comments(
    ticket_id: str,
    roots: Annotated[bool, typer.Option("--roots", help="Show only root comments.")] = False,
    thread: Annotated[str | None, typer.Option("--thread", help="Show one thread by thread id or comment id.")] = None,
    recent_threads: Annotated[
        int,
        typer.Option("--recent-threads", "--recent", help="Show recent active threads."),
    ] = 0,
    tail: Annotated[int | None, typer.Option("--tail", help="Show the last N comments.")] = None,
    since: Annotated[str | None, typer.Option("--since", help="Show comments created after this timestamp.")] = None,
) -> None:
    """Show Build Ticket comments."""
    store = AriadneStore(state.root)
    ticket = store.resolve_ticket(ticket_id)
    if sum([bool(roots), bool(thread), recent_threads > 0]) > 1:
        typer.echo("Use only one of --roots, --thread, or --recent-threads.")
        raise typer.Exit(2)
    if tail is not None and tail < 1:
        typer.echo("--tail must be greater than 0.")
        raise typer.Exit(2)
    if recent_threads < 0:
        typer.echo("--recent-threads must be greater than or equal to 0.")
        raise typer.Exit(2)
    if recent_threads and (tail is not None or since is not None):
        typer.echo("--recent-threads cannot be combined with --tail or --since.")
        raise typer.Exit(2)
    if thread:
        comments = store.list_comment_thread(ticket.id, thread)
    elif roots:
        comments = store.list_comment_roots(ticket.id)
    elif recent_threads:
        threads = store.list_recent_comment_threads(ticket.id, limit=recent_threads)
        if not threads:
            typer.echo("No comments.")
            return
        for index, thread_comments in enumerate(threads, start=1):
            root = thread_comments[0]
            latest = thread_comments[-1]
            typer.echo(
                f"thread {index}: {root.thread_id}\tcomments={len(thread_comments)}\t"
                f"latest={latest.created_at}\troot={root.body}"
            )
        return
    else:
        comments = store.list_comments(ticket.id, since=since, tail=tail)
    if since is not None and (thread or roots):
        comments = [comment for comment in comments if comment.created_at > since]
    if tail is not None and (thread or roots):
        comments = comments[-tail:]
    if not comments:
        typer.echo("No comments.")
        return
    for comment in comments:
        typer.echo(_format_comment(comment))


def _format_comment(comment: TicketComment) -> str:
    parent = comment.parent_comment_id or ""
    return (
        f"{comment.created_at}\t{comment.kind.value}\t"
        f"{comment.author_type.value}:{comment.author}\t"
        f"id={comment.id}\tthread={comment.thread_id}\tparent={parent}\t"
        f"{comment.body}"
    )


@ticket_app.command("handoffs")
def ticket_handoffs(ticket_id: str) -> None:
    """Show Agent handoffs for a Build Ticket."""
    store = AriadneStore(state.root)
    ticket = store.resolve_ticket(ticket_id)
    handoffs = store.list_handoffs_for_ticket(ticket.id)
    if not handoffs:
        typer.echo("No handoffs.")
        return
    for handoff in handoffs:
        typer.echo(
            f"{handoff.from_agent} -> {handoff.to_agent}\t{handoff.status.value}\t"
            f"{handoff.reason}\t{handoff.payload_ref or ''}"
        )


@ticket_app.command("resume")
def ticket_resume(ticket_id: str) -> None:
    """Create a conservative resume plan for a ticket."""
    store = AriadneStore(state.root)
    ticket = store.resolve_ticket(ticket_id)
    plan = build_resume_plan(store, ticket)
    if plan.safety is not ResumeSafety.SAFE_TO_RESUME:
        assignment = store.find_latest_assignment_for_ticket(ticket.id)
        store.add_comment(
            ticket,
            CommentAuthorType.SYSTEM,
            "Recovery",
            CommentKind.RECOVERY,
            f"Resume blocked: {'; '.join(plan.reasons)}",
            payload_ref=plan.id,
            thread_id=assignment.id if assignment else None,
        )
        typer.echo(f"blocked: {plan.safety.value}")
        for reason in plan.reasons:
            typer.echo(f"- {reason}")
        raise typer.Exit(2)
    typer.echo(f"safe_to_resume: {plan.recommended_command}")


@ticket_app.command("retry")
def ticket_retry(
    ticket_id: str,
    reason: Annotated[str, typer.Option("--reason")] = "retry requested",
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    """Create a retry assignment for the latest blocked or failed assignment on a ticket."""
    store = AriadneStore(state.root)
    ticket = store.resolve_ticket(ticket_id)
    assignment = store.find_latest_assignment_for_ticket(ticket.id)
    if assignment is None:
        typer.echo(f"No assignment found for {ticket.key}.")
        raise typer.Exit(2)
    try:
        retry = create_retry_assignment(store, assignment, reason, force)
    except ValueError as exc:
        typer.echo(str(exc))
        raise typer.Exit(2) from exc
    typer.echo(f"retry assignment: {retry.id}")
    typer.echo(f"ticket: {ticket.key}")
    typer.echo(f"parent: {retry.parent_assignment_id}")
    typer.echo(f"attempt: {retry.attempt}")


@ticket_app.command("supersede")
def ticket_supersede(
    ticket_id: str,
    reason: Annotated[str, typer.Option("--reason", help="Why this ticket is superseded.")],
) -> None:
    """Supersede a Build Ticket and record a backlog update."""
    store = AriadneStore(state.root)
    try:
        ticket = store.resolve_ticket(ticket_id)
    except FileNotFoundError as exc:
        typer.echo(str(exc))
        raise typer.Exit(2) from exc
    update = supersede_ticket(store, ticket, reason)
    updated = store.load_ticket(ticket.id)
    typer.echo(f"superseded: {updated.key}")
    typer.echo(f"status: {updated.status.value}")
    typer.echo(f"backlog update: {update.id}")
    typer.echo(f"reason: {reason}")


@run_app.command("messages")
def run_messages(
    run_id: str,
    since: Annotated[int, typer.Option("--since", help="Exclusive run message sequence cursor.")] = 0,
) -> None:
    """Print one Agent Run message stream as deterministic JSONL."""
    if since < 0:
        typer.echo("--since must be greater than or equal to 0.")
        raise typer.Exit(2)
    store = AriadneStore(state.root)
    try:
        store.load_run(run_id)
    except FileNotFoundError as exc:
        typer.echo(f"unknown run: {run_id}")
        raise typer.Exit(2) from exc
    for message in store.list_run_messages(run_id, since=since):
        typer.echo(
            json.dumps(
                message.model_dump(mode="json", exclude_none=False),
                sort_keys=True,
                separators=(",", ":"),
            )
        )


@ticket_app.command("plan")
def ticket_plan(
    ticket_id: str,
    planner: Annotated[str, typer.Option("--planner", help="deterministic|llm")] = "deterministic",
) -> None:
    """Plan an existing Build Ticket into a Build Packet and handoff artifact."""
    store = AriadneStore(state.root)
    ticket = store.resolve_ticket(ticket_id)
    result = planner_for_name(planner).plan_ticket(store, ticket)
    if not result.succeeded:
        typer.echo(f"planner blocked: {result.error}")
        typer.echo(f"artifact: {result.error_artifact_path}")
        raise typer.Exit(2)
    typer.echo(f"planned {ticket.key} with {result.planner_name}")
    typer.echo(f"build packet: {result.build_packet_id}")
    typer.echo(f"handoff: {result.handoff_artifact_path}")


@ticket_app.command("run")
def ticket_run(
    ticket_id: str,
    backend: Annotated[str, typer.Option("--backend", help="dry-run|fake-codex|shell|codex|claude-code")] = "fake-codex",
    target_repo_path: Annotated[
        Path | None,
        typer.Option("--target-repo-path", help="Target repository path. Defaults to demo target."),
    ] = None,
    command: Annotated[str | None, typer.Option("--command", help="Override backend command.")] = None,
    planner: Annotated[str, typer.Option("--planner", help="deterministic|llm")] = "deterministic",
    confirm_execution: Annotated[bool, typer.Option("--confirm-execution")] = False,
    isolate_worktree: Annotated[
        bool,
        typer.Option("--isolate-worktree", help="Create a per-ticket git branch/worktree before execution."),
    ] = False,
) -> None:
    """Run a Build Ticket through the full Ariadne product loop."""
    result = TicketRunOrchestrator(AriadneStore(state.root)).run_ticket(
        ticket_id,
        backend_name=backend,
        target_repo_path=str(target_repo_path) if target_repo_path else None,
        command=command,
        planner=planner,
        confirm_execution=confirm_execution,
        isolate_worktree=isolate_worktree,
    )
    typer.echo(f"ran {result.ticket_key} ({result.ticket_id})")
    typer.echo(f"backend used: {result.backend_name}")
    typer.echo(f"changed files: {', '.join(result.changed_files)}")
    typer.echo(f"test exit code: {result.test_exit_code}")
    typer.echo(f"reviewer verdict: {result.review_verdict}")
    typer.echo(f"memory: {result.memory_path}")
    typer.echo(f"feishu plan: {result.feishu_plan_path}")
    typer.echo(f"next tickets: {result.next_tickets_path}")
    typer.echo(f"backlog updates: {', '.join(result.backlog_update_ids)}")
    if result.worktree_path:
        typer.echo(f"worktree: {result.worktree_path}")
    typer.echo(f"board: {result.board_path}")


@ticket_app.command("execute")
def ticket_execute(
    ticket_id: str,
    backend: Annotated[str, typer.Option("--backend", help="dry-run|fake-codex|shell|codex")] = "dry-run",
    command: Annotated[str, typer.Option("--command", help="Command for shell/codex backends.")] = "",
    confirm_execution: Annotated[bool, typer.Option("--confirm-execution")] = False,
) -> None:
    """Execute a ticket against the demo target project."""
    store = AriadneStore(state.root)
    ticket = store.resolve_ticket(ticket_id)
    if not ticket.build_packet_id:
        raise typer.BadParameter("ticket has no Build Packet")
    packet = store.load_build_packet(ticket.build_packet_id)
    target = ensure_demo_target_project(state.root)
    context = ExecutionContext(
        ticket_id=ticket.id,
        build_packet_id=packet.id,
        target_repo_path=str(target),
        handoff_prompt=f"Execute {ticket.key}: {ticket.title}",
        backend_name=backend,
        allowed_paths=packet.affected_modules,
        command=command or "Add demo-todo export-json support",
        test_command=target_test_command(),
        confirm_execution=confirm_execution,
    )
    result = backend_for_name(backend).execute(context)
    store.save_execution_result(result)
    ticket = ticket.with_status(TicketStatus.CODING, "Execution")
    ticket = ticket.model_copy(update={"metadata": ticket.metadata | {"execution_result_id": result.id}})
    store.save_ticket(ticket)
    typer.echo(f"execution result: {result.id}")
    typer.echo(f"exit code: {result.exit_code}")
    typer.echo(f"test exit code: {result.test_exit_code}")


@ticket_app.command("review")
def ticket_review(ticket_id: str) -> None:
    """Review a ticket execution result."""
    store = AriadneStore(state.root)
    ticket = store.resolve_ticket(ticket_id)
    if not ticket.build_packet_id:
        raise typer.BadParameter("ticket has no Build Packet")
    packet = store.load_build_packet(ticket.build_packet_id)
    execution = None
    if ticket.metadata.get("execution_result_id"):
        execution = store.load_execution_result(ticket.metadata["execution_result_id"])
    review = review_execution(store, ticket, packet, execution)
    store.save_review_report(review)
    typer.echo(f"reviewer verdict: {review.verdict.value}")


@daemon_app.command("run-once")
def daemon_run_once(
    runtime_id: Annotated[str, typer.Option("--runtime-id")] = "local",
    confirm_execution: Annotated[bool, typer.Option("--confirm-execution")] = False,
) -> None:
    """Claim and run one queued assignment."""
    result = LocalDaemonWorker(AriadneStore(state.root), runtime_id=runtime_id).run_once(
        confirm_execution=confirm_execution,
    )
    if not result.did_work:
        typer.echo("no work")
        return
    typer.echo(f"Assignment claimed: {result.assignment_id}")
    typer.echo(f"running ticket: {result.ticket_key}")
    if result.ticket_run_result:
        typer.echo(f"reviewer verdict: {result.ticket_run_result.review_verdict}")
        typer.echo(f"board: {result.ticket_run_result.board_path}")
    typer.echo(f"assignment {result.status}: {result.assignment_id}")


@daemon_app.command("start")
def daemon_start(
    runtime_id: Annotated[str, typer.Option("--runtime-id")] = "local",
    interval: Annotated[float, typer.Option("--interval")] = 5.0,
    max_iterations: Annotated[int | None, typer.Option("--max-iterations")] = None,
    confirm_execution: Annotated[bool, typer.Option("--confirm-execution")] = False,
) -> None:
    """Run a simple local daemon polling loop."""
    LocalDaemonWorker(AriadneStore(state.root), runtime_id=runtime_id).run_loop(
        interval_seconds=interval,
        max_iterations=max_iterations,
        confirm_execution=confirm_execution,
    )
    typer.echo("daemon loop finished")


@daemon_app.command("status")
def daemon_status() -> None:
    """Show local daemon queue status."""
    store = AriadneStore(state.root)
    open_assignments = store.list_open_assignments()
    heartbeats = store.list_worker_heartbeats()
    events = store.list_runtime_events()
    if heartbeats:
        for heartbeat in heartbeats:
            typer.echo(f"runtime_id: {heartbeat.runtime_id}")
            typer.echo(f"pid: {heartbeat.pid}")
            typer.echo(f"status: {heartbeat.status.value}")
            typer.echo(f"current ticket: {heartbeat.current_ticket_key or ''}")
            typer.echo(f"current assignment: {heartbeat.current_assignment_id or ''}")
            typer.echo(f"current stage: {heartbeat.current_stage or ''}")
            typer.echo(f"heartbeat_at: {heartbeat.heartbeat_at}")
            typer.echo(f"last event: {heartbeat.last_event_id or ''}")
            typer.echo(f"stale: {str(is_stale_heartbeat(heartbeat)).lower()}")
    else:
        typer.echo("runtime_id: local")
        typer.echo("status: unknown")
        typer.echo("stale: unknown")
    typer.echo(f"open assignments: {len(open_assignments)}")
    typer.echo(
        "running assignments: "
        f"{sum(1 for assignment in open_assignments if assignment.status is AssignmentStatus.RUNNING)}"
    )
    typer.echo(
        "blocked assignments: "
        f"{sum(1 for assignment in store.list_assignments() if assignment.status is AssignmentStatus.BLOCKED)}"
    )
    if events:
        last = events[-1]
        typer.echo(f"last journal event: {last.stage}:{last.event_type}")


@runtime_app.command("journal")
def runtime_journal(
    limit: Annotated[int, typer.Option("--limit")] = 20,
) -> None:
    """Show recent runtime journal events."""
    events = AriadneStore(state.root).list_runtime_events()[-limit:]
    if not events:
        typer.echo("No runtime journal events.")
        return
    for event in events:
        typer.echo(
            f"{event.timestamp}\t{event.ticket_key or ''}\t{event.assignment_id or ''}\t"
            f"{event.stage}\t{event.event_type}\t{event.actor}"
        )


@runtime_app.command("recover")
def runtime_recover() -> None:
    """Scan local runtime state and print conservative resume plans."""
    store = AriadneStore(state.root)
    plans = [build_resume_plan(store, ticket) for ticket in store.list_tickets()]
    if not plans:
        typer.echo("No tickets to recover.")
        return
    for plan in plans:
        if plan.assignment_id is None:
            continue
        typer.echo(f"{plan.ticket_key}\t{plan.safety.value}\tcurrent={plan.current_stage or ''}")
        for reason in plan.reasons:
            typer.echo(f"- {reason}")
        if plan.recommended_command:
            typer.echo(f"recommended: {plan.recommended_command}")


@runtime_app.command("locks")
def runtime_locks(
    force_stale_locks: Annotated[bool, typer.Option("--force-stale-locks")] = False,
) -> None:
    """List local directory locks and optionally clear stale ones."""
    store = AriadneStore(state.root)
    locks = list_locks(store)
    if not locks:
        typer.echo("No locks.")
        return
    for lock in locks:
        typer.echo(
            f"{lock.target_path}\tpid={lock.pid}\tticket={lock.ticket_id or ''}\t"
            f"assignment={lock.assignment_id or ''}\tstale={lock.stale}"
        )
    cleared = clear_stale_locks(store, force=force_stale_locks)
    if cleared:
        typer.echo(f"cleared stale locks: {len(cleared)}")


@export_app.command("board")
def export_board_command() -> None:
    """Export a static markdown Build Board."""
    board_path = export_board(AriadneStore(state.root))
    typer.echo(f"Board exported: {board_path}")


@board_app.command("serve")
def board_serve(
    port: Annotated[int, typer.Option("--port")] = 8765,
) -> None:
    """Serve the local static board with Python's stdlib HTTP server."""
    board_serve_command(AriadneStore(state.root).board_dir, port=port)


@doctor_app.command("secrets")
def doctor_secrets() -> None:
    """Report secret-related environment variables without printing values."""
    from ariadne_ltb.doctor import secret_status_lines

    for line in secret_status_lines(state.root):
        typer.echo(line)


@doctor_app.command("store")
def doctor_store(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the machine-readable store invariant report."),
    ] = False,
    stale_lock_seconds: Annotated[
        int,
        typer.Option("--stale-lock-seconds", help="Seconds before a directory lock is stale."),
    ] = 3600,
) -> None:
    """Validate local .ariadne store invariants without repairing state."""
    from ariadne_ltb.store_doctor import check_store_invariants, store_invariant_human_lines

    store = AriadneStore(state.root)
    report = check_store_invariants(store, stale_lock_seconds=stale_lock_seconds)
    report_path = store.doctor_dir / "store_invariants.json"
    if json_output:
        typer.echo(report.model_dump_json(indent=2, exclude_none=False))
    else:
        for line in store_invariant_human_lines(report, report_path):
            typer.echo(line)
    if report.error_count:
        raise typer.Exit(2)


@doctor_app.command("v1")
def doctor_v1() -> None:
    """Run local read-only Ariadne v1 readiness checks."""
    from ariadne_ltb.doctor import v1_readiness_lines

    store = AriadneStore(state.root)
    for line in v1_readiness_lines(store, state.root):
        typer.echo(line)


@memory_app.command("export")
def memory_export(ticket_id: str) -> None:
    """Export local memory for a reviewed ticket."""
    store = AriadneStore(state.root)
    ticket = store.resolve_ticket(ticket_id)
    packet = store.load_build_packet(ticket.build_packet_id)
    execution = store.load_execution_result(ticket.metadata["execution_result_id"])
    review_id = ticket.metadata.get("review_report_id")
    review = store.load_review_report(review_id) if review_id else review_execution(store, ticket, packet, execution)
    record, path = write_memory_record(store, ticket, packet, execution, review)
    plan, feishu_path = generate_feishu_plan(store, ticket, packet, execution, review)
    typer.echo(f"memory record: {record.id} {path}")
    typer.echo(f"feishu dry-run plan: {plan.id} {feishu_path}")


@memory_app.command("sync")
def memory_sync(
    ticket_id: str,
    target: Annotated[str, typer.Option("--target")] = "feishu",
    dry_run: Annotated[bool, typer.Option("--dry-run")] = True,
    confirm_write: Annotated[bool, typer.Option("--confirm-write")] = False,
) -> None:
    """Preview optional Feishu sync; real writes are disabled by default."""
    if target != "feishu":
        raise typer.BadParameter("only --target feishu is supported")
    if not dry_run and not confirm_write:
        raise typer.BadParameter("real Feishu writes require --confirm-write")
    store = AriadneStore(state.root)
    ticket = store.resolve_ticket(ticket_id)
    plan_id = ticket.metadata.get("feishu_write_plan_id")
    if not plan_id:
        typer.echo(f"No Feishu plan found for {ticket.key}; run `ari demo full` or `ari memory export` first.")
        return
    plan = store.load_feishu_write_plan(plan_id)
    if dry_run:
        typer.echo(f"Feishu dry-run plan for {ticket.key}: {plan.id}")
        typer.echo(plan.run_summary)
        return
    result = create_lark_doc_from_plan(plan, store.memory_dir / "feishu_sync", confirm_write)
    typer.echo(__import__("json").dumps(result, indent=2, ensure_ascii=False))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
