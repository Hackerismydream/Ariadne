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
from ariadne_ltb.application.project_versions import ProjectVersionService
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
        from ariadne_ltb.knowledge import compile_issues_with_provenance

        compile_result = compile_issues_with_provenance(
            self.store,
            project_id=context.manifest.target_project_id,
            title=title,
            north_star=north_star,
            context=context,
        )
        tasks = compile_result.specs
        compiler_provenance = compile_result.provenance.model_dump()
        operations: list[BacklogOperation] = []
        existing_tickets = self.store.list_tickets()
        existing_keys = {ticket.key for ticket in existing_tickets}
        prefix = _issue_prefix(self.store, context.manifest.target_project_id, title)
        next_index = _next_ticket_index(existing_keys, prefix)
        existing_by_title = {}
        target_version_label = _target_version_label(self.store, context.manifest.target_project_id)
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
            evidence_refs = _select_evidence_refs(task, context)
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
                        "target_version_label": target_version_label,
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
                        "compiler_provenance": compiler_provenance,
                        "codebase_snapshot_artifact_id": context.manifest.codebase_snapshot_artifact_id,
                        "codebase_snapshot_status": context.manifest.codebase_snapshot_status,
                        "codebase_snapshot_reason": context.manifest.codebase_snapshot_reason,
                        "target_project_id": context.manifest.target_project_id,
                        "goal_reason": task.reason,
                        "source_claim_trace": _source_claim_trace(evidence_refs, context),
                        "affected_module_rationale": _affected_module_rationale(task, context),
                        "acceptance_criteria_rationale": _acceptance_criteria_rationale(task, context),
                        "risks": task.risks,
                        "assumptions": task.assumptions,
                    },
                )
            )
            if not existing_ticket:
                next_index += 1
        return operations


def _select_evidence_refs(task: CompiledIssueSpec, context: IssueFactoryContext) -> list[str]:
    if not context.evidence:
        return task.evidence_refs or context.manifest.evidence_ids
    requested = [item for item in task.evidence_refs if item in {evidence.id for evidence in context.evidence}]
    if requested and len(requested) <= 5:
        return requested
    haystack = " ".join([task.title, task.reason, *task.affected_modules, *task.acceptance_criteria]).lower()
    scored: list[tuple[int, str]] = []
    for evidence in context.evidence:
        text = " ".join([evidence.claim, evidence.quote_or_summary, evidence.locator]).lower()
        score = sum(1 for token in _meaningful_tokens(haystack) if token in text)
        if evidence.id in requested:
            score += 3
        scored.append((score, evidence.id))
    selected = [evidence_id for score, evidence_id in sorted(scored, reverse=True) if score > 0][:5]
    if selected:
        return selected
    return [item.id for item in context.evidence[:3]]


def _meaningful_tokens(text: str) -> set[str]:
    stop = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "that",
        "this",
        "into",
        "code",
        "task",
        "issue",
        "agent",
    }
    return {
        token.strip(".,:;()[]{}").lower()
        for token in text.replace("/", " ").replace("_", " ").replace("-", " ").split()
        if len(token.strip(".,:;()[]{}")) >= 4 and token.lower() not in stop
    }


def _source_claim_trace(evidence_refs: list[str], context: IssueFactoryContext) -> list[dict[str, object]]:
    evidence_by_id = {item.id: item for item in context.evidence}
    return [
        {
            "evidence_id": evidence.id,
            "source_document_id": evidence.source_document_id,
            "claim": evidence.claim,
            "locator": evidence.locator,
            "confidence": evidence.confidence,
            "quote_or_summary": evidence.quote_or_summary,
        }
        for evidence_id in evidence_refs
        for evidence in [evidence_by_id.get(evidence_id)]
        if evidence is not None
    ]


def _affected_module_rationale(task: CompiledIssueSpec, context: IssueFactoryContext) -> str:
    snapshot = context.manifest.codebase_snapshot_status
    modules = ", ".join(task.affected_modules[:4]) or "target modules"
    if snapshot == "present":
        return f"Modules selected from task scope and current target codebase snapshot: {modules}."
    return f"Modules selected from source evidence because target codebase snapshot is {snapshot}: {modules}."


def _acceptance_criteria_rationale(task: CompiledIssueSpec, context: IssueFactoryContext) -> str:
    evidence_count = len(_source_claim_trace(_select_evidence_refs(task, context), context))
    return (
        f"Acceptance criteria are derived from {evidence_count} source claim(s), "
        f"the project goal, and snapshot status {context.manifest.codebase_snapshot_status}."
    )


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


def _target_version_label(store: AriadneStore, target_project_id: str) -> str:
    versions = ProjectVersionService(store).list()
    current = ProjectVersionService(store).current()
    if current and current.target_project_id == target_project_id:
        return current.version_label
    for version in versions:
        if version.target_project_id == target_project_id:
            return version.version_label
    return "current"


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
            "origin_bucket": "internal_synthetic",
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
        metadata={
            "entrypoint": "web_issue_factory",
            "origin_bucket": "internal_synthetic",
            "evidence_snippets": [north_star],
        },
    )
