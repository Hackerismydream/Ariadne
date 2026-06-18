from __future__ import annotations

from hashlib import sha256

from ariadne_ltb.application.dtos import (
    BacklogPreviewDTO,
    IssueFactoryApplyOutput,
    IssueFactoryPreviewInput,
)
from ariadne_ltb.application.mappers import backlog_preview_dto
from ariadne_ltb.application.project_goals import ProjectGoalService
from ariadne_ltb.backlog import apply_backlog_preview, ticket_backlog_fingerprint
from ariadne_ltb.models import (
    BacklogOperation,
    BacklogOperationType,
    BacklogPreview,
    BacklogUpdateTrigger,
    SourceDocument,
    SourceType,
    TicketStatus,
    stable_id,
)
from ariadne_ltb.storage import AriadneStore


class IssueFactoryService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def preview(self, payload: IssueFactoryPreviewInput) -> BacklogPreviewDTO:
        goal = ProjectGoalService(self.store).load(payload.goal_id)
        sources = self._sources(payload.source_ids)
        fingerprint = ticket_backlog_fingerprint(self.store)
        seed = "|".join([goal.id, goal.title, goal.north_star, fingerprint, *[source.id for source in sources]])
        idempotency_key = stable_id("issue_factory", seed)
        preview_id = stable_id("backlog_preview", idempotency_key)
        existing = self._load_existing(preview_id)
        if existing:
            return backlog_preview_dto(existing)

        operations = self._operations(goal.title, goal.north_star, sources, payload.target_project_id)
        preview = BacklogPreview(
            id=preview_id,
            trigger_type=BacklogUpdateTrigger.MANUAL_GOAL,
            trigger_ref=goal.id,
            idempotency_key=idempotency_key,
            base_ticket_fingerprint=fingerprint,
            operations=operations,
            rationale=(
                "Generated an issue set from the active builder goal, selected external knowledge, "
                "and current local project context."
            ),
            evidence_refs=[goal.id, *[source.id for source in sources]],
        )
        self.store.save_backlog_preview(preview)
        return backlog_preview_dto(preview)

    def apply(self, preview_id: str) -> IssueFactoryApplyOutput:
        result = apply_backlog_preview(self.store, preview_id)
        update = result.update
        return IssueFactoryApplyOutput(
            preview=backlog_preview_dto(result.preview),
            created_ticket_ids=update.created_ticket_ids if update else [],
            updated_ticket_ids=update.updated_ticket_ids if update else [],
            superseded_ticket_ids=update.superseded_ticket_ids if update else [],
            already_applied=result.already_applied,
        )

    def _sources(self, source_ids: list[str]) -> list[SourceDocument]:
        if source_ids:
            return [self.store.load_source_document(source_id) for source_id in source_ids]
        return self.store.list_source_documents()

    def _load_existing(self, preview_id: str) -> BacklogPreview | None:
        try:
            return self.store.load_backlog_preview(preview_id)
        except FileNotFoundError:
            return None

    def _operations(
        self,
        title: str,
        north_star: str,
        sources: list[SourceDocument],
        target_project_id: str | None,
    ) -> list[BacklogOperation]:
        tasks = _dogfood_tasks() if _is_mini_code_goal(title, north_star, sources) else _generic_tasks(title)
        operations: list[BacklogOperation] = []
        existing_keys = {ticket.key for ticket in self.store.list_tickets()}
        next_index = _next_ticket_index(existing_keys)
        primary_source = sources[0] if sources else _synthetic_source(title, north_star)
        for task in tasks:
            while f"ARI-{next_index:03d}" in existing_keys:
                next_index += 1
            ticket_key = f"ARI-{next_index:03d}"
            existing_keys.add(ticket_key)
            source_doc = _source_for_task(primary_source, task, target_project_id)
            ticket_id = stable_id("ticket", source_doc.id, ticket_key)
            operations.append(
                BacklogOperation(
                    id=stable_id("backlog_op", ticket_id, task["title"]),
                    operation_type=BacklogOperationType.ADD_TICKET,
                    ticket_id=ticket_id,
                    ticket_key=ticket_key,
                    title=task["title"],
                    description=task["reason"],
                    source_type=source_doc.source_type.value,
                    source_ref=source_doc.path_or_url,
                    priority=task["priority"],
                    status=TicketStatus.PLANNING,
                    reason=task["reason"],
                    metadata={
                        "source_document": source_doc.model_dump(mode="json"),
                        "owner_agent": task["owner_agent"],
                        "build_decision": task["build_decision"],
                        "acceptance_criteria": task["acceptance_criteria"],
                        "affected_modules": task["affected_modules"],
                        "evidence_refs": [primary_source.id],
                        "target_project_id": target_project_id,
                    },
                )
            )
            next_index += 1
        return operations


def _next_ticket_index(existing_keys: set[str]) -> int:
    values = []
    for key in existing_keys:
        if key.startswith("ARI-"):
            try:
                values.append(int(key.split("-", 1)[1]))
            except ValueError:
                continue
    return (max(values) + 1) if values else 1


def _is_mini_code_goal(title: str, north_star: str, sources: list[SourceDocument]) -> bool:
    haystack = " ".join([title, north_star, *[source.title + " " + source.path_or_url for source in sources]]).lower()
    return any(token in haystack for token in ["mini code", "mini-code", "mini-swe", "minimal-agent"])


def _dogfood_tasks() -> list[dict[str, object]]:
    return [
        _task(
            "Define Mini Code Agent product contract",
            "Lock the builder-facing contract for a local mini code agent before implementation.",
            "high",
            ["docs/product/mini-code-agent-contract.md"],
        ),
        _task(
            "Implement Mini Code Agent workspace model",
            "Represent a folder-backed builder project with goal, sources, issue set, and execution state.",
            "high",
            ["mini_code_agent/workspace.py", "tests/test_workspace.py"],
        ),
        _task(
            "Implement external knowledge ingestion for Mini Code Agent",
            "Accept blog, GitHub repo notes, and markdown snippets as first-class project sources.",
            "high",
            ["mini_code_agent/knowledge.py", "tests/test_knowledge.py"],
        ),
        _task(
            "Implement Issue Factory for Mini Code Agent",
            "Generate versioned issue deltas from goal, knowledge, codebase state, and feedback.",
            "high",
            ["mini_code_agent/issues.py", "tests/test_issue_factory.py"],
        ),
        _task(
            "Implement Codex and Claude execution adapter surface",
            "Route approved issues to real coding backends through safety-gated adapters.",
            "high",
            ["mini_code_agent/runtime.py", "tests/test_runtime.py"],
        ),
        _task(
            "Show trajectory, diff, tests, and review evidence",
            "Persist and expose the evidence a builder needs to trust each agent run.",
            "medium",
            ["mini_code_agent/evidence.py", "tests/test_evidence.py"],
        ),
    ]


def _generic_tasks(title: str) -> list[dict[str, object]]:
    return [
        _task(
            f"Clarify product contract for {title}",
            "Turn the goal and selected knowledge into an explicit implementation contract.",
            "high",
            ["docs/product/contract.md"],
        ),
        _task(
            f"Implement first vertical slice for {title}",
            "Build the smallest end-to-end version that proves the goal can move through planning, execution, and review.",
            "high",
            ["src/", "tests/"],
        ),
        _task(
            f"Add evidence and review loop for {title}",
            "Record diff, tests, review verdict, and next issue suggestions for future iterations.",
            "medium",
            ["src/evidence", "tests/"],
        ),
    ]


def _task(title: str, reason: str, priority: str, affected_modules: list[str]) -> dict[str, object]:
    return {
        "title": title,
        "reason": reason,
        "priority": priority,
        "owner_agent": "Build Lead",
        "build_decision": "code_task",
        "acceptance_criteria": [
            "The implementation is reachable from the Web Workbench product path.",
            "The resulting behavior writes inspectable evidence.",
            "Tests cover the new behavior without external credentials.",
        ],
        "affected_modules": affected_modules,
    }


def _source_for_task(
    primary: SourceDocument,
    task: dict[str, object],
    target_project_id: str | None,
) -> SourceDocument:
    content = f"{primary.id}\n{task['title']}\n{task['reason']}"
    return SourceDocument(
        id=stable_id("source", primary.id, task["title"]),
        source_type=primary.source_type,
        title=str(task["title"]),
        path_or_url=primary.path_or_url,
        content_hash=sha256(content.encode("utf-8")).hexdigest(),
        summary=str(task["reason"]),
        metadata={
            "entrypoint": "web_issue_factory",
            "parent_source_id": primary.id,
            "target_project_id": target_project_id,
            "evidence_snippets": [str(task["reason"])],
        },
    )


def _synthetic_source(title: str, north_star: str) -> SourceDocument:
    content = f"{title}\n{north_star}"
    return SourceDocument(
        id=stable_id("source", "goal", title, north_star),
        source_type=SourceType.NOTE,
        title=title,
        path_or_url="ariadne://goal",
        content_hash=sha256(content.encode("utf-8")).hexdigest(),
        summary=north_star,
        metadata={"entrypoint": "web_issue_factory", "evidence_snippets": [north_star]},
    )
