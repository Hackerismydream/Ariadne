from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import BuildDecision, ReviewVerdict, SourceType
from ariadne_ltb.orchestrator import TicketRunOrchestrator
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project


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
    next_tickets_path: Path


def default_source_fixtures() -> list[Path]:
    return sorted((Path(__file__).resolve().parents[1] / "examples" / "sources").glob("*.md"))


def run_full_demo(
    root: str | Path = ".",
    source_paths: list[Path] | None = None,
    backend_name: str = "fake-codex",
    confirm_execution: bool = False,
    timeout_seconds: int = 60,
) -> FullDemoResult:
    root_path = Path(root).resolve()
    store = AriadneStore(root_path)
    ensure_demo_target_project(root_path)
    sources = source_paths or default_source_fixtures()
    tickets = ingest_sources(store, sources)
    selected = select_code_task_ticket(store, tickets)
    result = TicketRunOrchestrator(store).run_ticket(
        selected.key,
        backend_name=backend_name,
        target_repo_path=str(root_path / ".ariadne" / "demo_target_project"),
        confirm_execution=confirm_execution,
        timeout_seconds=timeout_seconds,
    )
    return FullDemoResult(
        sources_ingested=len(sources),
        tickets_created=len(tickets),
        selected_ticket_id=result.ticket_id,
        selected_ticket_key=result.ticket_key,
        backend_name=result.backend_name,
        execution_result_id=result.execution_result_id,
        changed_files=result.changed_files,
        test_exit_code=result.test_exit_code,
        review_verdict=ReviewVerdict(result.review_verdict),
        board_path=Path(result.board_path),
        board_html_path=Path(result.board_html_path),
        memory_path=Path(result.memory_path),
        feishu_plan_path=Path(result.feishu_plan_path),
        next_tickets_path=Path(result.next_tickets_path),
    )


def select_code_task_ticket(store: AriadneStore, tickets: list) -> object:
    for ticket in tickets:
        packet = store.load_build_packet(ticket.build_packet_id)
        if (
            ticket.source_type == SourceType.GITHUB_REPO.value
            and packet.build_decision is BuildDecision.CODE_TASK
        ):
            return ticket
    for ticket in tickets:
        packet = store.load_build_packet(ticket.build_packet_id)
        if packet.build_decision is BuildDecision.CODE_TASK:
            return ticket
    msg = "no code_task ticket found"
    raise RuntimeError(msg)
