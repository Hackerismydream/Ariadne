from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from ariadne_ltb.models import (
    BuildDecision,
    BuildPacket,
    BuildTicket,
    Evidence,
    SourceDocument,
    SourceType,
    TicketEvent,
    TicketStatus,
    stable_id,
    utc_now,
)
from ariadne_ltb.storage import AriadneStore


def ingest_sources(store: AriadneStore, paths: list[Path]) -> list[BuildTicket]:
    tickets: list[BuildTicket] = []
    next_index = 1
    existing_by_source = {
        ticket.metadata.get("source_document_id"): ticket for ticket in store.list_tickets()
    }
    for path in sorted(paths, key=lambda item: item.name):
        document = source_document_from_path(path)
        store.save_source_document(document)
        if document.id in existing_by_source:
            ticket = existing_by_source[document.id]
        else:
            ticket = ticket_from_source(document, next_ticket_key(store, next_index))
            next_index += 1
        packet = build_packet_from_source(ticket, document)
        store.save_build_packet(packet)
        ticket = ticket.model_copy(
            deep=True,
            update={"build_packet_id": packet.id, "status": TicketStatus.PLANNING},
        ).append_event(
            "source_ingested",
            "Source Router",
            f"Ingested {document.source_type.value} source: {document.title}.",
            payload_ref=document.id,
        )
        store.save_ticket(ticket)
        tickets.append(ticket)
    return sorted(tickets, key=lambda ticket: ticket.key)


def source_document_from_path(path: Path) -> SourceDocument:
    content = path.read_text(encoding="utf-8")
    content_hash = sha256(content.encode("utf-8")).hexdigest()
    source_type = infer_source_type(path, content)
    title = infer_title(path, content)
    summary = summarize_source(source_type, content)
    return SourceDocument(
        id=stable_id("source", content_hash),
        source_type=source_type,
        title=title,
        path_or_url=str(path.resolve()),
        content_hash=content_hash,
        summary=summary,
        metadata={"filename": path.name},
    )


def infer_title(path: Path, content: str) -> str:
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("_", " ").title()


def infer_source_type(path: Path, content: str) -> SourceType:
    haystack = f"{path.name}\n{content}".lower()
    if "github" in haystack or "readme" in haystack:
        return SourceType.GITHUB_REPO
    if "blog" in haystack or "multica" in haystack:
        return SourceType.BLOG
    if "paper" in haystack or "method" in haystack or "evaluation" in haystack:
        return SourceType.PAPER
    return SourceType.NOTE


def summarize_source(source_type: SourceType, content: str) -> str:
    sentences = " ".join(line.strip() for line in content.splitlines() if line.strip())
    summary = sentences[:260].rstrip()
    return f"{source_type.value} source: {summary}"


def next_ticket_key(store: AriadneStore, offset: int = 1) -> str:
    used = {ticket.key for ticket in store.list_tickets()}
    candidate = offset
    while True:
        key = f"ARI-{candidate:03d}"
        if key not in used:
            return key
        candidate += 1


def ticket_from_source(source: SourceDocument, key: str) -> BuildTicket:
    created_at = utc_now()
    return BuildTicket(
        id=stable_id("ticket", source.id),
        key=key,
        title=title_for_ticket(source),
        description=source.summary,
        source_type=source.source_type.value,
        source_ref=source.path_or_url,
        status=TicketStatus.INBOX,
        priority="high" if source.source_type is SourceType.GITHUB_REPO else "medium",
        owner_agent="Build Lead",
        created_at=created_at,
        updated_at=created_at,
        metadata={"source_document_id": source.id},
        event_log=[
            TicketEvent(
                timestamp=created_at,
                ticket_id=stable_id("ticket", source.id),
                event_type="ticket_created",
                actor="Source Router",
                summary=f"Created ticket from {source.source_type.value} source.",
                payload_ref=source.id,
            )
        ],
    )


def title_for_ticket(source: SourceDocument) -> str:
    if source.source_type is SourceType.GITHUB_REPO:
        return "Add JSON export command to demo target CLI"
    if source.source_type is SourceType.PAPER:
        return "Evaluate Build Packet quality from evidence-backed agent workflow notes"
    if source.source_type is SourceType.BLOG:
        return "Improve board timeline visibility from Multica collaboration lessons"
    return source.title


def build_packet_from_source(ticket: BuildTicket, source: SourceDocument) -> BuildPacket:
    decision = decision_for_source(source)
    evidence = [
        Evidence(
            id=stable_id("evidence", source.id, "primary"),
            source_ref=source.path_or_url,
            quote_or_summary=source.summary,
            location=source.metadata.get("filename", "source"),
            confidence=0.86,
        )
    ]
    tasks, criteria, modules = packet_work_items(source)
    return BuildPacket(
        id=stable_id("packet", ticket.id),
        ticket_id=ticket.id,
        source_summary=source.summary,
        insight=insight_for_source(source),
        evidence=evidence,
        project_relevance=relevance_for_source(source),
        build_decision=decision,
        tasks=tasks,
        acceptance_criteria=criteria,
        affected_modules=modules,
        risks=["Scope creep if the source is treated as a full platform rewrite."],
        assumptions=["1.0 uses deterministic local rules unless optional adapters are confirmed."],
        confidence=0.86,
    )


def decision_for_source(source: SourceDocument) -> BuildDecision:
    if source.source_type is SourceType.GITHUB_REPO:
        return BuildDecision.CODE_TASK
    if source.source_type is SourceType.PAPER:
        return BuildDecision.EXPERIMENT
    if source.source_type is SourceType.BLOG:
        return BuildDecision.DOC_UPDATE
    return BuildDecision.WATCHLIST


def insight_for_source(source: SourceDocument) -> str:
    if source.source_type is SourceType.GITHUB_REPO:
        return "A small CLI can add value through a focused JSON export command with tests."
    if source.source_type is SourceType.PAPER:
        return "Agent workflow quality should be evaluated through evidence coverage and acceptance clarity."
    if source.source_type is SourceType.BLOG:
        return "Visible issue/run timelines make agent collaboration auditable."
    return "Source should be tracked for future build relevance."


def relevance_for_source(source: SourceDocument) -> str:
    if source.source_type is SourceType.GITHUB_REPO:
        return "Maps directly to the demo target project feature `demo-todo export-json`."
    if source.source_type is SourceType.PAPER:
        return "Informs a future Build Packet quality evaluator."
    if source.source_type is SourceType.BLOG:
        return "Informs richer board and run timeline visibility."
    return "Useful as project memory."


def packet_work_items(source: SourceDocument) -> tuple[list[str], list[str], list[str]]:
    if source.source_type is SourceType.GITHUB_REPO:
        return (
            ["Add `demo-todo export-json` to the demo target CLI.", "Add tests for JSON output."],
            [
                "`demo-todo export-json` exists.",
                "Output is a valid JSON list.",
                "Target project tests pass.",
                "Changed files stay inside the target project.",
            ],
            ["demo_todo/cli.py", "tests/test_cli.py"],
        )
    if source.source_type is SourceType.PAPER:
        return (
            ["Design Build Packet quality scoring dimensions."],
            ["Quality dimensions include evidence coverage, acceptance clarity, and scope risk."],
            ["ariadne_ltb/review.py"],
        )
    if source.source_type is SourceType.BLOG:
        return (
            ["Improve board timeline fields for attempts and execution status."],
            ["Board shows run attempts, backend, exit code, and test result."],
            ["ariadne_ltb/board.py"],
        )
    return (["Archive source for future review."], ["Source remains visible in memory."], ["docs/"])
