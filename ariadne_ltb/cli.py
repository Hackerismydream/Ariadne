from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ariadne_ltb.board import export_board
from ariadne_ltb.demo import create_demo_ticket, default_source_path, ensure_project_space, run_demo
from ariadne_ltb.runtime import PipelineEngine, RuntimeContext
from ariadne_ltb.agents import default_pipeline_nodes
from ariadne_ltb.storage import AriadneStore

app = typer.Typer(help="Ariadne local deterministic Learning-to-Build workbench.")
ticket_app = typer.Typer(help="Build Ticket commands.")
export_app = typer.Typer(help="Export commands.")
app.add_typer(ticket_app, name="ticket")
app.add_typer(export_app, name="export")


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
def demo() -> None:
    """Run the deterministic Ariadne MVP demo pipeline."""
    result = run_demo(root=state.root)
    typer.echo(f"Created and ran {result.ticket_key} ({result.ticket_id})")
    typer.echo(f"Artifacts: {result.artifacts_dir}")
    typer.echo(f"Board: {result.board_path}")


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
    ticket = store.load_ticket(ticket_id)
    typer.echo(f"{ticket.key}: {ticket.title}")
    typer.echo(f"Status: {ticket.status.value}")
    typer.echo(f"Source: {ticket.source_ref}")
    typer.echo(f"Runs: {len(ticket.agent_run_ids)}")
    typer.echo(f"Artifacts: {len(ticket.artifact_ids)}")


@ticket_app.command("run")
def ticket_run(ticket_id: str) -> None:
    """Run the deterministic pipeline for an existing Build Ticket."""
    store = AriadneStore(state.root)
    ticket = store.load_ticket(ticket_id)
    source_path = Path(ticket.source_ref)
    source_text = source_path.read_text(encoding="utf-8")
    context = RuntimeContext(store=store, ticket=ticket, source_text=source_text, source_path=source_path)
    final_ticket = PipelineEngine(default_pipeline_nodes()).run(context)
    typer.echo(f"Ran {final_ticket.key} ({final_ticket.id})")


@export_app.command("board")
def export_board_command() -> None:
    """Export a static markdown Build Board."""
    board_path = export_board(AriadneStore(state.root))
    typer.echo(f"Board exported: {board_path}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
