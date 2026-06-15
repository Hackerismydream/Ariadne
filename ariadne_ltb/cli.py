from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Annotated

import typer

from ariadne_ltb.board import export_board
from ariadne_ltb.demo import create_demo_ticket, default_source_path, ensure_project_space, run_demo
from ariadne_ltb.execution import CodexBackend, backend_for_name
from ariadne_ltb.feishu import create_lark_doc_from_plan
from ariadne_ltb.full_demo import default_source_fixtures, run_full_demo, select_code_task_ticket
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.memory import generate_feishu_plan, write_memory_record
from ariadne_ltb.orchestrator import TicketRunOrchestrator
from ariadne_ltb.planner import planner_for_name
from ariadne_ltb.review import review_execution
from ariadne_ltb.runtime import collect_runtime_capabilities
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project, target_test_command
from ariadne_ltb.models import ExecutionContext, TicketStatus

app = typer.Typer(help="Ariadne local deterministic Learning-to-Build workbench.")
ticket_app = typer.Typer(help="Build Ticket commands.")
export_app = typer.Typer(help="Export commands.")
memory_app = typer.Typer(help="Memory commands.")
backend_app = typer.Typer(help="Execution backend diagnostics and smoke tests.")
app.add_typer(ticket_app, name="ticket")
app.add_typer(export_app, name="export")
app.add_typer(memory_app, name="memory")
app.add_typer(backend_app, name="backend")


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


@backend_app.command("doctor")
def backend_doctor() -> None:
    """Report local backend availability and safety-gate state without secrets."""
    store = AriadneStore(state.root)
    store.save_runtime_capabilities(collect_runtime_capabilities())
    codex_path = shutil.which("codex")
    claude_path = shutil.which("claude")
    typer.echo("FakeCodexBackend: available")
    typer.echo("ShellBackend: available")
    typer.echo(f"CodexBackend command: {'found ' + codex_path if codex_path else 'missing'}")
    typer.echo(f"ClaudeCodeBackend command: {'found ' + claude_path if claude_path else 'missing'}")
    for variable in [
        "ARIADNE_ENABLE_EXTERNAL_EXECUTION",
        "ARIADNE_CODEX_COMMAND_TEMPLATE",
        "ARIADNE_CLAUDE_COMMAND_TEMPLATE",
        "FEISHU_ENABLE_WRITE",
        "DEEPSEEK_API_KEY",
    ]:
        typer.echo(f"{variable}: {'set' if os.environ.get(variable) else 'unset'}")


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


@ticket_app.command("list")
def ticket_list() -> None:
    """List Build Tickets."""
    for ticket in AriadneStore(state.root).list_tickets():
        typer.echo(f"{ticket.key}\t{ticket.status.value}\t{ticket.source_type}\t{ticket.title}")


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
) -> None:
    """Run a Build Ticket through the full Ariadne product loop."""
    result = TicketRunOrchestrator(AriadneStore(state.root)).run_ticket(
        ticket_id,
        backend_name=backend,
        target_repo_path=str(target_repo_path) if target_repo_path else None,
        command=command,
        planner=planner,
        confirm_execution=confirm_execution,
    )
    typer.echo(f"ran {result.ticket_key} ({result.ticket_id})")
    typer.echo(f"backend used: {result.backend_name}")
    typer.echo(f"changed files: {', '.join(result.changed_files)}")
    typer.echo(f"test exit code: {result.test_exit_code}")
    typer.echo(f"reviewer verdict: {result.review_verdict}")
    typer.echo(f"memory: {result.memory_path}")
    typer.echo(f"feishu plan: {result.feishu_plan_path}")
    typer.echo(f"next tickets: {result.next_tickets_path}")
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


@export_app.command("board")
def export_board_command() -> None:
    """Export a static markdown Build Board."""
    board_path = export_board(AriadneStore(state.root))
    typer.echo(f"Board exported: {board_path}")


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
