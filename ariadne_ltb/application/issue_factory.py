from __future__ import annotations

from hashlib import sha256

from ariadne_ltb.application.build_context import IssueFactoryContext, assemble_issue_factory_context
from ariadne_ltb.application.dtos import (
    BacklogPreviewDTO,
    IssueFactoryApplyOutput,
    IssueFactoryPreviewInput,
)
from ariadne_ltb.application.issue_compiler import CompiledIssueSpec
from ariadne_ltb.application.issue_delta_validation import validate_issue_delta_operations
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
        context = assemble_issue_factory_context(self.store, goal, sources, payload.target_project_id)
        seed = "|".join([goal.id, context.manifest.context_fingerprint, fingerprint])
        idempotency_key = stable_id("issue_factory", seed)
        preview_id = stable_id("backlog_preview", idempotency_key)
        existing = self._load_existing(preview_id)
        if existing:
            return backlog_preview_dto(existing)

        operations = validate_issue_delta_operations(self._operations(goal.title, goal.north_star, context))
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
            evidence_refs=[goal.id, *context.manifest.evidence_ids],
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
        context: IssueFactoryContext,
    ) -> list[BacklogOperation]:
        from ariadne_ltb.knowledge import compile_issues

        tasks = compile_issues(
            self.store,
            project_id=context.manifest.target_project_id,
            title=title,
            north_star=north_star,
            context=context,
        )
        operations: list[BacklogOperation] = []
        existing_tickets = self.store.list_tickets()
        existing_keys = {ticket.key for ticket in existing_tickets}
        prefix = _issue_prefix(self.store, context.manifest.target_project_id, title)
        next_index = _next_ticket_index(existing_keys, prefix)
        existing_by_title = {}
        for ticket in sorted(existing_tickets, key=lambda item: item.key):
            if not ticket.key.startswith(f"{prefix}-"):
                continue
            if ticket.metadata.get("target_project_id") != context.manifest.target_project_id:
                continue
            existing_by_title.setdefault(ticket.title.strip().lower(), ticket)
        primary_source = context.sources[0] if context.sources else _synthetic_source(title, north_star)
        source_artifact_ids = context.manifest.source_artifact_ids
        source_document_ids = context.manifest.source_document_ids
        for task in tasks:
            evidence_refs = task.evidence_refs or context.manifest.evidence_ids or [primary_source.id]
            source_doc = _source_for_task(primary_source, task, context, evidence_refs)
            existing_ticket = existing_by_title.get(task.title.strip().lower())
            if existing_ticket:
                ticket_key = existing_ticket.key
                ticket_id = existing_ticket.id
                operation_type = BacklogOperationType.UPDATE_TICKET
                change_intent = "update"
            else:
                while f"{prefix}-{next_index:03d}" in existing_keys:
                    next_index += 1
                ticket_key = f"{prefix}-{next_index:03d}"
                ticket_id = stable_id("ticket", source_doc.id, ticket_key)
                operation_type = BacklogOperationType.ADD_TICKET
                existing_keys.add(ticket_key)
                change_intent = "add"
            operations.append(
                BacklogOperation(
                    id=stable_id("backlog_op", ticket_id, task.title),
                    operation_type=operation_type,
                    ticket_id=ticket_id,
                    ticket_key=ticket_key,
                    title=task.title,
                    description=task.reason,
                    source_type=source_doc.source_type.value,
                    source_ref=source_doc.path_or_url,
                    priority=task.priority,
                    status=TicketStatus.PLANNING,
                    reason=task.reason,
                    metadata={
                        "source_document": source_doc.model_dump(mode="json"),
                        "issue_class": "mainline",
                        "origin": "issue_factory",
                        "root_ticket_key": ticket_key,
                        "change_intent": change_intent,
                        "target_version_label": context.manifest.metadata.get("target_version_label", "v0.1")
                        if hasattr(context.manifest, "metadata")
                        else "v0.1",
                        "existing_ticket_key": existing_ticket.key if existing_ticket else None,
                        "after_summary": task.reason,
                        "confidence": 0.75,
                        "decision_reason": task.reason,
                        "included": True,
                        "owner_agent": task.owner_agent,
                        "build_decision": task.build_decision,
                        "acceptance_criteria": task.acceptance_criteria,
                        "affected_modules": task.affected_modules,
                        "evidence_refs": evidence_refs,
                        "source_document_ids": source_document_ids,
                        "source_artifact_ids": source_artifact_ids,
                        "build_context_id": context.manifest.id,
                        "context_fingerprint": context.manifest.context_fingerprint,
                        "target_project_id": context.manifest.target_project_id,
                        "goal_reason": task.reason,
                        "risks": task.risks,
                        "assumptions": task.assumptions,
                    },
                )
            )
            if not existing_ticket:
                next_index += 1
        return operations


def _next_ticket_index(existing_keys: set[str], prefix: str) -> int:
    values = []
    for key in existing_keys:
        if key.startswith(f"{prefix}-"):
            try:
                values.append(int(key.split("-", 1)[1]))
            except ValueError:
                continue
    return (max(values) + 1) if values else 1


def _issue_prefix(store: AriadneStore, target_project_id: str, title: str) -> str:
    for resource in store.load_project_resources():
        if resource.id == target_project_id:
            prefix = resource.resource_ref.get("issue_prefix")
            if prefix:
                return _normalize_prefix(str(prefix))
            label = resource.label or resource.resource_ref.get("label")
            if label:
                return _prefix_from_label(str(label))
    if "mini code" in title.lower() or "mini-code" in title.lower():
        return "MCA"
    return _prefix_from_label(title)


def _normalize_prefix(value: str) -> str:
    cleaned = "".join(char for char in value.upper() if char.isalnum())
    return cleaned[:4] or "PRJ"


def _prefix_from_label(value: str) -> str:
    if "mini code" in value.lower() or "mini-code" in value.lower():
        return "MCA"
    words = ["".join(char for char in word.upper() if char.isalnum()) for word in value.replace("-", " ").split()]
    letters = "".join(word[0] for word in words if word)
    return (letters or "PRJ")[:4]


def _is_mini_code_context(title: str, north_star: str, context: IssueFactoryContext) -> bool:
    haystack = " ".join(
        [
            title,
            north_star,
            *[source.title + " " + source.path_or_url for source in context.sources],
        ]
    ).lower()
    return any(token in haystack for token in ["mini code", "mini-code", "mini-swe", "minimal-agent"])


def _mini_code_agent_tasks() -> list[dict[str, object]]:
    return [
        _task(
            "Bootstrap Python package and CLI",
            "A minimal coding agent needs an executable package and command-line entrypoint before higher-level agent behavior can be tested.",
            "high",
            ["pyproject.toml", "mini_code_agent/__main__.py", "mini_code_agent/cli.py", "tests/test_cli.py", ".mini-code-agent/"],
        ),
        _task(
            "Add DeepSeek-backed LLM client configuration",
            "The target agent needs a real upstream model client and local configuration path instead of demo responses.",
            "high",
            ["mini_code_agent/llm.py", "mini_code_agent/config.py", "tests/test_llm_config.py"],
        ),
        _task(
            "Define tool protocol and model action schema",
            "Reference projects converge on a model-action-observation loop, so the target needs a typed protocol before tool execution.",
            "high",
            ["mini_code_agent/protocol.py", "tests/test_protocol.py"],
        ),
        _task(
            "Implement shell command tool with allowlist",
            "Coding agents need shell access, but the first version must restrict commands to an explicit allowlist.",
            "high",
            ["mini_code_agent/tools/shell.py", "tests/test_shell_tool.py"],
        ),
        _task(
            "Implement file read and patch tools with review-before-write safety",
            "Reference agents expose file operations, but Ariadne should dogfood review-before-write safety in the target agent.",
            "high",
            ["mini_code_agent/tools/files.py", "tests/test_file_tools.py"],
        ),
        _task(
            "Implement agent loop: prompt -> action -> observation -> repeat",
            "The core agent value is the loop that turns model actions into tool observations until the task is complete or blocked.",
            "high",
            ["mini_code_agent/agent_loop.py", "tests/test_agent_loop.py"],
        ),
        _task(
            "Persist session trace and run summary",
            "AI Builders need inspectable trajectories to debug and improve the mini code agent.",
            "medium",
            ["mini_code_agent/trace.py", "tests/test_trace.py"],
        ),
        _task(
            "Capture git diff and test result",
            "The target agent must report changed files, diff, and tests so the builder can review output.",
            "high",
            ["mini_code_agent/evidence.py", "tests/test_evidence.py"],
        ),
        _task(
            "Add minimal reviewer checks for task completion",
            "A conservative reviewer pass is needed before a run can be considered usable.",
            "medium",
            ["mini_code_agent/reviewer.py", "tests/test_reviewer.py"],
        ),
        _task(
            "Write README quickstart and usage examples",
            "A v0.1 is not usable unless an AI Builder can install it, run it, and inspect output.",
            "medium",
            ["README.md", "docs/quickstart.md"],
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
        "risks": ["Scope should stay small enough for one issue-sized coding pass."],
        "assumptions": ["The target project is a local Python package managed from the Ariadne Workbench."],
    }


def _source_for_task(
    primary: SourceDocument,
    task: CompiledIssueSpec,
    context: IssueFactoryContext,
    evidence_refs: list[str],
) -> SourceDocument:
    content = f"{primary.id}\n{task.title}\n{task.reason}"
    return SourceDocument(
        id=stable_id("source", primary.id, task.title),
        source_type=primary.source_type,
        title=task.title,
        path_or_url=primary.path_or_url,
        content_hash=sha256(content.encode("utf-8")).hexdigest(),
        summary=task.reason,
        metadata={
            "entrypoint": "web_issue_factory",
            "parent_source_id": primary.id,
            "target_project_id": context.manifest.target_project_id,
            "build_context_id": context.manifest.id,
            "source_artifact_ids": context.manifest.source_artifact_ids,
            "evidence_refs": evidence_refs,
            "evidence_snippets": [task.reason],
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
