from __future__ import annotations

from collections import Counter, defaultdict

from ariadne_ltb.application.dtos import IssueChildDTO, IssueFamilyDTO, IssueProjectionDTO
from ariadne_ltb.models import BuildTicket, TicketStatus
from ariadne_ltb.storage import AriadneStore


def build_issue_projection(store: AriadneStore, tickets: list[BuildTicket] | None = None) -> IssueProjectionDTO:
    tickets = sorted(tickets if tickets is not None else store.list_tickets(), key=lambda item: item.key)
    classified = [(ticket, *classify_ticket(ticket)) for ticket in tickets]
    children_by_root: dict[str, list[tuple[BuildTicket, str, str, str]]] = defaultdict(list)
    mainline: dict[str, BuildTicket] = {}
    repair_items: list[IssueChildDTO] = []
    history_items: list[IssueChildDTO] = []

    for ticket, issue_class, origin, root_key in classified:
        if issue_class == "mainline":
            mainline[root_key] = ticket
            continue
        children_by_root[root_key].append((ticket, issue_class, origin, root_key))
        child = _child(ticket, issue_class, origin, root_key)
        if issue_class == "repair":
            repair_items.append(child)
        else:
            history_items.append(child)

    families: list[IssueFamilyDTO] = []
    for ticket in mainline.values():
        children = children_by_root.get(ticket.key, [])
        repair_children = [child for child in children if child[1] == "repair"]
        open_repairs = [child for child in repair_children if child[0].status not in {TicketStatus.DONE, TicketStatus.SUPERSEDED}]
        families.append(
            IssueFamilyDTO(
                ticket_id=ticket.id,
                ticket_key=ticket.key,
                title=ticket.title,
                status=ticket.status.value,
                priority=ticket.priority,
                root_ticket_key=ticket.key,
                repair_count=len(repair_children),
                open_repair_count=len(open_repairs),
                history_count=len(children) - len(repair_children),
                child_ticket_keys=[child[0].key for child in children],
                latest_repair_summary=open_repairs[-1][0].title if open_repairs else None,
            )
        )

    # If historical data has children but no explicit root ticket, surface a synthetic family
    # by using the child itself. This prevents hidden work without flooding the default view.
    for root_key, children in children_by_root.items():
        if root_key in mainline:
            continue
        ticket = children[0][0]
        families.append(
            IssueFamilyDTO(
                ticket_id=ticket.id,
                ticket_key=root_key,
                title=f"{root_key} related work",
                status=ticket.status.value,
                priority=ticket.priority,
                root_ticket_key=root_key,
                repair_count=sum(1 for child in children if child[1] == "repair"),
                open_repair_count=sum(
                    1
                    for child in children
                    if child[1] == "repair" and child[0].status not in {TicketStatus.DONE, TicketStatus.SUPERSEDED}
                ),
                history_count=sum(1 for child in children if child[1] != "repair"),
                child_ticket_keys=[child[0].key for child in children],
            )
        )

    counts = Counter(issue_class for _, issue_class, _, _ in classified)
    return IssueProjectionDTO(
        summary=dict(counts | Counter({"total": len(tickets)})),
        mainline_tickets=sorted(families, key=lambda item: item.ticket_key),
        repair_items=repair_items,
        history_items=history_items,
    )


def classify_ticket(ticket: BuildTicket) -> tuple[str, str, str]:
    metadata = ticket.metadata
    issue_class = metadata.get("issue_class")
    if issue_class:
        return (
            str(issue_class),
            str(metadata.get("origin") or "manual"),
            str(metadata.get("root_ticket_key") or metadata.get("parent_ticket_key") or ticket.key),
        )
    if metadata.get("source_ticket_key") or metadata.get("parent_ticket_key"):
        return (
            "repair",
            str(metadata.get("origin") or "inbox_recovery"),
            str(metadata.get("source_ticket_key") or metadata.get("parent_ticket_key")),
        )
    if metadata.get("generated_from_ticket_key"):
        return ("generated_followup", "llm_next_ticket", str(metadata["generated_from_ticket_key"]))
    title = ticket.title.lower()
    if title.startswith("repair ") or title.startswith("fix review") or "repair execution" in title:
        return ("repair", "repair_inferred", str(metadata.get("root_ticket_key") or ticket.key))
    if ticket.status in {TicketStatus.SUPERSEDED}:
        return ("history", "superseded", str(metadata.get("root_ticket_key") or ticket.key))
    return ("mainline", str(metadata.get("origin") or "issue_factory"), ticket.key)


def _child(ticket: BuildTicket, issue_class: str, origin: str, root_key: str) -> IssueChildDTO:
    return IssueChildDTO(
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        title=ticket.title,
        issue_class=issue_class,
        origin=origin,
        status=ticket.status.value,
        parent_ticket_key=str(ticket.metadata.get("parent_ticket_key") or ticket.metadata.get("source_ticket_key") or root_key),
        root_ticket_key=root_key,
        reason=str(ticket.metadata.get("goal_reason") or ticket.description),
    )
