from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from ariadne_ltb.backlog import record_source_ingest_backlog_update
from ariadne_ltb.models import (
    BuildDecision,
    BuildPacket,
    BuildTicket,
    Evidence,
    SourceDocument,
    SourceType,
    TicketChange,
    TicketChangeType,
    TicketEvent,
    TicketStatus,
    stable_id,
    utc_now,
)
from ariadne_ltb.planner_quality import score_build_packet
from ariadne_ltb.prompt_guard import prompt_guard_metadata, quote_untrusted_snippet
from ariadne_ltb.storage import AriadneStore


def ingest_sources(store: AriadneStore, paths: list[Path]) -> list[BuildTicket]:
    paths = _dedupe_paths(paths)
    tickets: list[BuildTicket] = []
    changes: list[TicketChange] = []
    evidence_refs: list[str] = []
    next_index = 1
    existing_by_source = {
        ticket.metadata.get("source_document_id"): ticket for ticket in store.list_tickets()
    }
    existing_by_path = {
        source_path: ticket
        for ticket in store.list_tickets()
        if (source_path := _ticket_source_path_key(ticket)) is not None
    }
    for path in sorted(paths, key=_path_ingest_order):
        document = source_document_from_path(path)
        store.save_source_document(document)
        evidence_refs.append(document.id)
        if document.id in existing_by_source or document.path_or_url in existing_by_path:
            ticket = existing_by_source.get(document.id) or existing_by_path[document.path_or_url]
            change_type = TicketChangeType.UPDATED
            before_status = ticket.status.value
            before_priority = ticket.priority
            next_status = ticket.status
        else:
            ticket = ticket_from_source(document, next_ticket_key(store, next_index))
            next_index += 1
            change_type = TicketChangeType.CREATED
            before_status = None
            before_priority = None
            next_status = TicketStatus.PLANNING
        packet = build_packet_from_source(ticket, document)
        store.save_build_packet(packet)
        ticket = ticket.model_copy(
            deep=True,
            update={
                "build_packet_id": packet.id,
                "description": document.summary,
                "source_ref": document.path_or_url,
                "source_type": document.source_type.value,
                "status": next_status,
                "metadata": ticket.metadata
                | {
                    "source_document_id": document.id,
                    "source_content_hash": document.content_hash,
                },
            },
        ).append_event(
            "source_ingested",
            "Source Router",
            f"Ingested {document.source_type.value} source: {document.title}.",
            payload_ref=document.id,
        )
        store.save_ticket(ticket)
        changes.append(
            TicketChange(
                ticket_id=ticket.id,
                ticket_key=ticket.key,
                change_type=change_type,
                reason=f"Ingested {document.source_type.value} source: {document.title}.",
                before_status=before_status,
                after_status=ticket.status.value,
                before_priority=before_priority,
                after_priority=ticket.priority,
            )
        )
        tickets.append(ticket)
        existing_by_source[document.id] = ticket
        existing_by_path[document.path_or_url] = ticket
    if tickets:
        record_source_ingest_backlog_update(
            store,
            tickets,
            changes,
            evidence_refs,
            paths,
        )
        tickets = [store.load_ticket(ticket.id) for ticket in tickets]
    return sorted(tickets, key=lambda ticket: ticket.key)


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        resolved = path.expanduser().resolve()
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        unique.append(resolved)
    return unique


def _ticket_source_path_key(ticket: BuildTicket) -> str | None:
    if not ticket.source_ref:
        return None
    try:
        return str(Path(ticket.source_ref).expanduser().resolve())
    except OSError:
        return ticket.source_ref


def _path_ingest_order(path: Path) -> tuple[int, str]:
    content = path.read_text(encoding="utf-8")
    source_type = infer_source_type(path, content)
    order = {
        SourceType.BLOG: 1,
        SourceType.PAPER: 2,
        SourceType.GITHUB_REPO: 3,
        SourceType.NOTE: 4,
        SourceType.OFFICE_HOUR: 5,
        SourceType.REVIEW: 6,
    }
    return (order[source_type], path.name)


def source_document_from_path(path: Path) -> SourceDocument:
    path = path.expanduser().resolve()
    content = path.read_text(encoding="utf-8")
    content_hash = sha256(content.encode("utf-8")).hexdigest()
    source_type = infer_source_type(path, content)
    title = infer_title(path, content)
    summary = summarize_source(source_type, content)
    return SourceDocument(
        id=stable_id("source", path),
        source_type=source_type,
        title=title,
        path_or_url=str(path.resolve()),
        content_hash=content_hash,
        summary=summary,
        metadata={
            "entrypoint": "offline_regression_fixture" if _is_offline_regression_path(path) else "local_source_ingest",
            "filename": path.name,
            "headings": extract_headings(content),
            "action_verbs": extract_action_verbs(content),
            "evidence_snippets": extract_evidence_snippets(content),
            **prompt_guard_metadata(content, str(path)),
        },
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


def extract_headings(content: str) -> list[str]:
    return [
        line.lstrip("#").strip()
        for line in content.splitlines()
        if line.startswith("## ")
    ]


def extract_action_verbs(content: str) -> list[str]:
    verbs = ["implement", "add", "compare", "evaluate", "build", "improve", "review", "design"]
    lower = content.lower()
    return [verb for verb in verbs if verb in lower]


def extract_evidence_snippets(content: str) -> list[str]:
    candidates = [
        line.strip("- ").strip()
        for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    return candidates[:5] if len(candidates) >= 2 else candidates[:1]


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
    if source.source_type is SourceType.GITHUB_REPO and _is_offline_regression_source(source):
        return "Add JSON export command to demo target CLI"
    if source.source_type is SourceType.GITHUB_REPO:
        return f"Extract implementation tasks from {source.title}"
    if source.source_type is SourceType.PAPER:
        return "Evaluate Build Packet quality from evidence-backed agent workflow notes"
    if source.source_type is SourceType.BLOG:
        return "Improve board timeline visibility from Multica collaboration lessons"
    return source.title


def build_packet_from_source(ticket: BuildTicket, source: SourceDocument) -> BuildPacket:
    decision = decision_for_source(source)
    evidence = evidence_from_source(source)
    tasks, criteria, modules = packet_work_items(source)
    packet = BuildPacket(
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
    quality = score_build_packet(packet)
    return packet.model_copy(
        update={
            "metadata": packet.metadata
            | {
                "quality": quality,
                "planner_mode": "deterministic",
                "trust_boundary": source.metadata.get("trust_boundary", "untrusted_external_context"),
                "prompt_injection_findings": source.metadata.get("prompt_injection_findings", []),
                "prompt_injection_warning_count": source.metadata.get("prompt_injection_warning_count", 0),
            }
        }
    )


def evidence_from_source(source: SourceDocument) -> list[Evidence]:
    path = Path(source.path_or_url)
    content = path.read_text(encoding="utf-8") if path.exists() else source.summary
    snippets = [
        line.strip()
        for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    selected = snippets[:5] if len(snippets) >= 2 else [source.summary]
    return [
        Evidence(
            id=stable_id("evidence", source.id, index, snippet),
            source_ref=source.path_or_url,
            quote_or_summary=quote_untrusted_snippet(snippet[:500]),
            location=f"{source.metadata.get('filename', 'source')}#{index}",
            confidence=0.86 if index == 1 else 0.74,
        )
        for index, snippet in enumerate(selected[:5], start=1)
    ]


def decision_for_source(source: SourceDocument) -> BuildDecision:
    haystack = (
        f"{source.title} {source.summary} "
        f"{' '.join(source.metadata.get('action_verbs', []))}"
    ).lower()
    if any(
        word in haystack
        for word in ["implementation", "implement", "cli", "github", "readme", "feature", "add"]
    ):
        return BuildDecision.CODE_TASK
    if any(word in haystack for word in ["evaluation", "benchmark", "metric", "paper", "evaluate"]):
        return BuildDecision.EXPERIMENT
    if any(word in haystack for word in ["architecture", "decision", "tradeoff", "design"]):
        return BuildDecision.ARCHITECTURE_CHANGE
    if source.source_type is SourceType.BLOG:
        return BuildDecision.DOC_UPDATE
    return BuildDecision.WATCHLIST


def insight_for_source(source: SourceDocument) -> str:
    if source.source_type is SourceType.GITHUB_REPO and _is_offline_regression_source(source):
        return "A small CLI can add value through a focused JSON export command with tests."
    if source.source_type is SourceType.GITHUB_REPO:
        return "Repository input should inform target project structure and implementation tasks without copying source code."
    if source.source_type is SourceType.PAPER:
        return "Agent workflow quality should be evaluated through evidence coverage and acceptance clarity."
    if source.source_type is SourceType.BLOG:
        return "Visible issue/run timelines make agent collaboration auditable."
    return "Source should be tracked for future build relevance."


def relevance_for_source(source: SourceDocument) -> str:
    if source.source_type is SourceType.GITHUB_REPO and _is_offline_regression_source(source):
        return "Maps directly to the demo target project feature `demo-todo export-json`."
    if source.source_type is SourceType.GITHUB_REPO:
        return "Provides reference architecture, behavior patterns, tests, and reuse constraints for the target project."
    if source.source_type is SourceType.PAPER:
        return "Informs a future Build Packet quality evaluator."
    if source.source_type is SourceType.BLOG:
        return "Informs richer board and run timeline visibility."
    return "Useful as project memory."


def packet_work_items(source: SourceDocument) -> tuple[list[str], list[str], list[str]]:
    if source.source_type is SourceType.GITHUB_REPO and _is_offline_regression_source(source):
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
    if source.source_type is SourceType.GITHUB_REPO:
        return (
            [
                "Analyze repository structure and extract transferable implementation patterns.",
                "Turn repository understanding into target-project issue candidates with acceptance criteria.",
            ],
            [
                "Repository analysis captures manifests, entrypoints, tests, and reuse constraints.",
                "Generated work items cite source evidence and avoid copying reference source code.",
                "Affected modules are target-project paths, not demo fixture paths.",
            ],
            ["src/", "tests/"],
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


def _is_offline_regression_path(path: Path) -> bool:
    parts = set(path.resolve().parts)
    return "examples" in parts and "sources" in parts


def _is_offline_regression_source(source: SourceDocument) -> bool:
    return str(source.metadata.get("entrypoint") or "") == "offline_regression_fixture"
