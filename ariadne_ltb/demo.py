from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ariadne_ltb.agents import default_pipeline_nodes
from ariadne_ltb.models import BuildTicket, ProjectSpace, TicketEvent, TicketStatus, stable_id, utc_now
from ariadne_ltb.runtime import PipelineEngine, RuntimeContext
from ariadne_ltb.storage import AriadneStore


@dataclass(frozen=True)
class DemoResult:
    ticket_id: str
    ticket_key: str
    artifacts_dir: Path
    board_path: Path


def default_source_path() -> Path:
    return Path(__file__).resolve().parents[1] / "examples" / "multica_research_note.md"


def create_demo_ticket(source_path: Path) -> BuildTicket:
    ticket_id = stable_id("ticket", "ARI-001", "multica_research_note")
    created_at = utc_now()
    return BuildTicket(
        id=ticket_id,
        key="ARI-001",
        title="Implement Ariadne MVP Ticket Kernel",
        description=(
            "Create a local deterministic Python Ticket Kernel that turns the Multica "
            "research note into a Build Packet, offline fixture execution, review, "
            "Feishu preview write plan, and static board."
        ),
        source_type="research_note",
        source_ref=str(source_path),
        status=TicketStatus.INBOX,
        owner_agent="Build Lead",
        created_at=created_at,
        updated_at=created_at,
        event_log=[
            TicketEvent(
                timestamp=created_at,
                ticket_id=ticket_id,
                event_type="ticket_created",
                actor="Ariadne Demo",
                summary="Created deterministic demo ticket from Multica research note.",
                payload_ref=str(source_path),
            )
        ],
        metadata={"demo": True},
    )


def ensure_project_space(store: AriadneStore) -> None:
    project = ProjectSpace(
        id="project_default",
        display_name="Ariadne",
        root_path=str(store.root),
        repo_path=str(store.root),
        knowledge_paths=[
            str(store.root / "docs" / "adr"),
            str(store.root / "templates"),
            str(store.root / "examples"),
        ],
        settings={
            "execution_backend": "dry_run",
            "external_writes": "plan_only",
        },
    )
    store.save_project_space(project)


def run_demo(root: str | Path = ".", source_path: str | Path | None = None) -> DemoResult:
    root_path = Path(root).resolve()
    source = Path(source_path).resolve() if source_path else default_source_path()
    if not source.exists():
        msg = f"source note does not exist: {source}"
        raise FileNotFoundError(msg)

    store = AriadneStore(root_path)
    ensure_project_space(store)
    ticket = create_demo_ticket(source)
    store.save_ticket(ticket)
    source_text = source.read_text(encoding="utf-8")
    context = RuntimeContext(store=store, ticket=ticket, source_text=source_text, source_path=source)
    final_ticket = PipelineEngine(default_pipeline_nodes()).run(context)

    from ariadne_ltb.board import export_board

    board_path = export_board(store)
    return DemoResult(
        ticket_id=final_ticket.id,
        ticket_key=final_ticket.key,
        artifacts_dir=store.artifacts_dir / final_ticket.id,
        board_path=board_path,
    )
