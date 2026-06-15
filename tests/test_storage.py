from __future__ import annotations

from pathlib import Path

from ariadne_ltb.models import (
    AgentRun,
    AgentRunStatus,
    ArtifactType,
    BuildTicket,
    ProjectSpace,
    TicketStatus,
)
from ariadne_ltb.storage import AriadneStore


def test_store_creates_inspectable_json_layout(tmp_path: Path) -> None:
    AriadneStore(tmp_path)

    assert (tmp_path / ".ariadne" / "tickets").is_dir()
    assert (tmp_path / ".ariadne" / "runs").is_dir()
    assert (tmp_path / ".ariadne" / "artifacts").is_dir()


def test_store_roundtrips_project_ticket_run_and_artifact(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    project = ProjectSpace(
        id="project_default",
        display_name="Ariadne",
        root_path=str(tmp_path),
        repo_path=str(tmp_path),
    )
    ticket = BuildTicket(
        id="ticket_demo",
        key="ARI-001",
        title="Implement Ariadne MVP Ticket Kernel",
        description="Demo ticket",
        source_type="research_note",
        source_ref="examples/multica_research_note.md",
        status=TicketStatus.INBOX,
    )
    run = AgentRun(
        id="run_demo",
        ticket_id=ticket.id,
        agent_name="Build Lead",
        agent_role="build_lead",
        status=AgentRunStatus.SUCCEEDED,
        input_summary="Route the ticket.",
        output_summary="Ticket should continue.",
    )

    store.save_project_space(project)
    store.save_ticket(ticket)
    store.save_run(run)
    artifact = store.write_artifact(
        ticket_id=ticket.id,
        agent_run_id=run.id,
        artifact_type=ArtifactType.RESEARCH_SUMMARY,
        filename="learning_summary.md",
        content="# Learning Summary\n\nVisible tickets matter.\n",
        summary="Learning summary",
    )

    loaded_ticket = store.load_ticket(ticket.id)
    loaded_run = store.load_run(run.id)

    assert loaded_ticket == ticket
    assert loaded_run == run
    assert Path(artifact.path).read_text(encoding="utf-8").startswith("# Learning Summary")


def test_list_tickets_reads_persisted_ticket_files(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    store.save_ticket(
        BuildTicket(
            id="ticket_demo",
            key="ARI-001",
            title="Implement Ariadne MVP Ticket Kernel",
            description="Demo ticket",
            source_type="research_note",
            source_ref="examples/multica_research_note.md",
            status=TicketStatus.DONE,
        )
    )

    assert [ticket.key for ticket in store.list_tickets()] == ["ARI-001"]
