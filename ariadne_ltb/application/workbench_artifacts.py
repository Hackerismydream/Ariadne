from __future__ import annotations

import json
from pathlib import Path

from ariadne_ltb.application.dtos import (
    IssueEvidenceDetailResponse,
    IssueEvidenceItemDTO,
    IssueEvidenceSectionDTO,
)
from ariadne_ltb.application.errors import NotFoundError
from ariadne_ltb.application.work_truth import reduce_work_truth
from ariadne_ltb.models import (
    Artifact,
    ArtifactType,
    BuildTicket,
    ExecutionResult,
    MemoryRecord,
    ReviewReport,
    RouteDecision,
    SourceArtifact,
    SourceDocument,
    SourceEvidence,
    TicketAssignment,
    TicketStatus,
    stable_id,
)
from ariadne_ltb.storage import AriadneStore


EXCERPT_LIMIT = 900
DETAIL_LIMIT = 8_000
JSON_PARSE_LIMIT = 64_000


class IssueEvidenceProjectionService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def sections(
        self,
        ticket: BuildTicket,
        assignments: list[TicketAssignment],
        executions: list[ExecutionResult],
        review: ReviewReport | None,
    ) -> list[IssueEvidenceSectionDTO]:
        items = [
            *self._source_items(ticket),
            *self._handoff_items(ticket, assignments, executions),
            *self._route_items(assignments),
            *self._execution_items(executions),
            *self._review_items(ticket, review),
            *self._memory_items(ticket),
            *self._next_ticket_items(ticket),
        ]
        labels = {
            "source": "Source Evidence",
            "handoff": "Handoff Evidence",
            "route": "Route Decision",
            "execution": "Execution Artifacts",
            "review": "Review Artifacts",
            "memory": "Memory Artifacts",
            "next_ticket": "Next Tickets",
        }
        sections: list[IssueEvidenceSectionDTO] = []
        for category, label in labels.items():
            category_items = [item for item in items if item.category == category]
            if category_items:
                sections.append(IssueEvidenceSectionDTO(category=category, label=label, items=category_items))
        return sections

    def detail(self, issue_id_or_key: str, evidence_id: str) -> IssueEvidenceDetailResponse:
        ticket = self._resolve_ticket(issue_id_or_key)
        assignments = self.store.list_assignments_for_ticket(ticket.id)
        executions = sorted(
            [result for result in self.store.list_execution_results() if result.ticket_id == ticket.id],
            key=lambda result: result.ended_at,
        )
        reports = [report for report in self.store.list_review_reports() if report.ticket_id == ticket.id]
        review = sorted(reports, key=lambda item: item.created_at)[-1] if reports else None
        all_items = [
            item
            for section in self.sections(ticket, assignments, executions, review)
            for item in section.items
        ]
        for item in all_items:
            if item.id == evidence_id:
                return IssueEvidenceDetailResponse(
                    issue_key=ticket.key,
                    evidence=item,
                    content_excerpt=self._full_content(item),
                )
        raise NotFoundError("issue evidence not found", {"issue": issue_id_or_key, "evidence_id": evidence_id})

    def _resolve_ticket(self, issue_id_or_key: str) -> BuildTicket:
        try:
            return self.store.resolve_ticket(issue_id_or_key)
        except FileNotFoundError as exc:
            raise NotFoundError(f"Issue not found: {issue_id_or_key}", {"issue": issue_id_or_key}) from exc

    def _source_items(self, ticket: BuildTicket) -> list[IssueEvidenceItemDTO]:
        source_ids = self._values(ticket, "source_document_id", "source_id")
        explicit_artifact_ids = self._values(ticket, "source_artifact_id", "codebase_snapshot_artifact_id")
        explicit_artifact_ids.extend(str(value) for value in ticket.metadata.get("source_artifact_ids", []) or [])
        source_artifact_ids = sorted(set(explicit_artifact_ids))

        evidence_ids = set(self._values(ticket, "evidence_id"))
        evidence_ids.update(str(value) for value in ticket.metadata.get("evidence_refs", []) or [])
        evidence_ids.update(str(value) for value in ticket.metadata.get("evidence_ids", []) or [])
        for artifact_id in source_artifact_ids:
            try:
                evidence_ids.update(self.store.load_source_artifact(artifact_id).evidence_ids)
            except FileNotFoundError:
                continue

        items: list[IssueEvidenceItemDTO] = []
        for source_id in sorted(set(source_ids)):
            try:
                source = self.store.load_source_document(source_id)
            except FileNotFoundError:
                items.append(
                    self._missing_item("source", "Source document", "source_document", source_id, f"Source document {source_id} is missing.")
                )
                continue
            items.append(self._source_document_item(source))

        for artifact_id in source_artifact_ids:
            if any(item.ref_id == artifact_id for item in items):
                continue
            try:
                artifact = self.store.load_source_artifact(artifact_id)
                source = self._try_source_document(artifact.source_document_id)
                items.append(self._source_artifact_item(artifact, source))
            except FileNotFoundError:
                items.append(
                    self._missing_item("source", "Source artifact", "source_artifact", artifact_id, f"Source artifact {artifact_id} is missing.")
                )

        for evidence_id in sorted(evidence_ids):
            if any(item.ref_id == evidence_id for item in items):
                continue
            try:
                evidence = self.store.load_source_evidence(evidence_id)
                source = self._try_source_document(evidence.source_document_id)
                items.append(self._source_evidence_item(evidence, source))
            except FileNotFoundError:
                items.append(
                    self._missing_item("source", "Source claim", "source_evidence", evidence_id, f"Source evidence {evidence_id} is missing.")
                )

        if not items and ticket.source_ref:
            items.append(
                IssueEvidenceItemDTO(
                    id=self._id(ticket.id, "source", "source_ref", ticket.source_ref),
                    category="source",
                    label="Ticket source reference",
                    ref_type="source_ref",
                    ref_id=ticket.source_ref,
                    path_or_url=ticket.source_ref,
                    validity="available",
                    summary=ticket.source_ref,
                    excerpt=ticket.source_ref,
                )
            )
        return items

    def _handoff_items(
        self,
        ticket: BuildTicket,
        assignments: list[TicketAssignment],
        executions: list[ExecutionResult],
    ) -> list[IssueEvidenceItemDTO]:
        items: list[IssueEvidenceItemDTO] = []
        packet_ids = [
            str(assignment.metadata["handoff_packet_id"])
            for assignment in assignments
            if assignment.metadata.get("handoff_packet_id")
        ]
        for packet_id in sorted(set(packet_ids)):
            try:
                packet = self.store.load_handoff_packet(packet_id)
            except FileNotFoundError:
                items.append(self._missing_item("handoff", "Handoff packet", "handoff_packet", packet_id, f"Handoff packet {packet_id} is missing."))
                continue
            item = self._file_item(
                category="handoff",
                label=f"Handoff packet {ticket.key}",
                ref_type="handoff_packet",
                ref_id=packet.id,
                path=packet.markdown_path,
                summary=f"{len(packet.evidence_refs)} evidence refs, {len(packet.acceptance_criteria)} acceptance criteria.",
                assignment_id=self._assignment_for_packet(assignments, packet.id),
                created_at=packet.created_at,
            )
            items.append(item)

        for execution in executions:
            if not execution.handoff_file:
                continue
            items.append(
                self._file_item(
                    category="handoff",
                    label=f"Execution handoff for {execution.backend_name}",
                    ref_type="handoff_file",
                    ref_id=execution.id,
                    path=execution.handoff_file,
                    summary=f"Prompt file used by {execution.backend_name}.",
                    assignment_id=execution.assignment_id,
                    execution_result_id=execution.id,
                    created_at=execution.started_at,
                )
            )

        if not items and assignments:
            items.append(
                IssueEvidenceItemDTO(
                    id=self._id(ticket.id, "handoff", "not_run"),
                    category="handoff",
                    label="Handoff",
                    ref_type="handoff_packet",
                    validity="not_run",
                    reason="No handoff packet or execution handoff file has been written for this assignment yet.",
                    summary="No handoff evidence is available yet.",
                )
            )
        return items

    def _route_items(self, assignments: list[TicketAssignment]) -> list[IssueEvidenceItemDTO]:
        items: list[IssueEvidenceItemDTO] = []
        route_ids = [
            str(assignment.metadata["route_decision_id"])
            for assignment in assignments
            if assignment.metadata.get("route_decision_id")
        ]
        for route_id in sorted(set(route_ids)):
            path = self.store.routes_dir / f"{route_id}.json"
            try:
                route = self.store.load_route_decision(route_id)
                summary = self._route_summary(route)
            except FileNotFoundError:
                items.append(self._missing_item("route", "Route decision", "route_decision", route_id, f"Route decision {route_id} is missing."))
                continue
            items.append(
                self._file_item(
                    category="route",
                    label=f"Route decision: {route.backend_name}",
                    ref_type="route_decision",
                    ref_id=route_id,
                    path=str(path),
                    summary=summary,
                    assignment_id=self._assignment_for_route(assignments, route_id),
                    created_at=route.created_at,
                )
            )
        return items

    def _execution_items(self, executions: list[ExecutionResult]) -> list[IssueEvidenceItemDTO]:
        items: list[IssueEvidenceItemDTO] = []
        for execution in executions:
            truth = reduce_work_truth(execution=execution)
            if execution.execution_log_artifact_id:
                items.append(self._artifact_item(execution.execution_log_artifact_id, "execution", execution=execution))
            else:
                items.append(self._execution_placeholder(execution, "execution_log", "Execution log", "No execution log artifact was recorded."))
            if execution.diff_artifact_id:
                items.append(self._artifact_item(execution.diff_artifact_id, "execution", execution=execution))
            else:
                reason = "No diff was produced." if execution.blocked else "No diff artifact was recorded."
                items.append(self._execution_placeholder(execution, "git_diff", "Git diff", reason))
            if truth.preflight_dirty_files:
                items.append(
                    IssueEvidenceItemDTO(
                        id=self._id(execution.id, "execution", "preflight_dirty"),
                        category="execution",
                        label="Preflight dirty files",
                        ref_type="preflight_dirty_files",
                        ref_id=execution.id,
                        validity="dirty_before_run",
                        reason="These files were dirty before the backend ran and are not agent-produced changes.",
                        summary=f"{len(truth.preflight_dirty_files)} pre-existing dirty files.",
                        excerpt="\n".join(truth.preflight_dirty_files),
                        assignment_id=execution.assignment_id,
                        execution_result_id=execution.id,
                        created_at=execution.started_at,
                    )
                )
            if execution.test_command:
                items.append(
                    IssueEvidenceItemDTO(
                        id=self._id(execution.id, "execution", "test_output"),
                        category="execution",
                        label="Test output",
                        ref_type="test_output",
                        ref_id=execution.id,
                        validity="produced_by_run" if execution.test_exit_code is not None else "not_run",
                        reason="" if execution.test_exit_code is not None else "Test command was planned but no test exit code was recorded.",
                        summary=f"{execution.test_command}: exit {execution.test_exit_code}",
                        excerpt=self._limit("\n".join(part for part in [execution.test_stdout, execution.test_stderr] if part), EXCERPT_LIMIT),
                        assignment_id=execution.assignment_id,
                        execution_result_id=execution.id,
                        created_at=execution.ended_at,
                    )
                )
        return items

    def _review_items(self, ticket: BuildTicket, review: ReviewReport | None) -> list[IssueEvidenceItemDTO]:
        reports = [report for report in self.store.list_review_reports() if report.ticket_id == ticket.id]
        if review and all(item.id != review.id for item in reports):
            reports.append(review)
        items: list[IssueEvidenceItemDTO] = []
        for report in sorted(reports, key=lambda item: item.created_at):
            path = self.store.reviews_dir / f"{report.id}.json"
            items.append(
                self._file_item(
                    category="review",
                    label=f"Review report: {report.verdict.value}",
                    ref_type="review_report",
                    ref_id=report.id,
                    path=str(path),
                    summary=f"{len(report.failed_checks)} failed checks, {len(report.warnings)} warnings.",
                    created_at=report.created_at,
                )
            )
        return items

    def _memory_items(self, ticket: BuildTicket) -> list[IssueEvidenceItemDTO]:
        try:
            record = self.store.load_memory_record(ticket.id)
        except FileNotFoundError:
            return [
                IssueEvidenceItemDTO(
                    id=self._id(ticket.id, "memory", "missing"),
                    category="memory",
                    label="Memory record",
                    ref_type="memory_record",
                    ref_id=ticket.id,
                    validity="missing",
                    reason="No memory record has been written for this ticket.",
                    summary="Memory is missing.",
                )
            ]
        path = self.store.memory_dir / "tickets" / f"{record.ticket_id}.json"
        return [self._memory_record_item(record, path)]

    def _next_ticket_items(self, ticket: BuildTicket) -> list[IssueEvidenceItemDTO]:
        children = sorted(
            [
                candidate
                for candidate in self.store.list_tickets()
                if candidate.metadata.get("generated_from_ticket_key") == ticket.key
                or candidate.metadata.get("source_ticket_key") == ticket.key
                or candidate.metadata.get("parent_ticket_key") == ticket.key
            ],
            key=lambda item: item.key,
        )
        items: list[IssueEvidenceItemDTO] = []
        for child in children:
            items.append(
                IssueEvidenceItemDTO(
                    id=self._id(ticket.id, "next_ticket", child.id),
                    category="next_ticket",
                    label=f"{child.key}: {child.title}",
                    ref_type="build_ticket",
                    ref_id=child.id,
                    validity="stale" if child.status is TicketStatus.SUPERSEDED else "available",
                    reason="This generated next ticket has been superseded." if child.status is TicketStatus.SUPERSEDED else "",
                    summary=f"{child.status.value} · {child.priority}",
                    excerpt=child.description,
                    created_at=child.created_at,
                )
            )
        for next_artifact in self._next_ticket_artifacts(ticket):
            items.append(
                self._file_item(
                    category="next_ticket",
                    label="Next tickets artifact",
                    ref_type="next_tickets_artifact",
                    ref_id=next_artifact.id,
                    path=next_artifact.path,
                    summary="Generated next-ticket artifact.",
                    created_at=next_artifact.created_at,
                )
            )
        return items

    def _next_ticket_artifacts(self, ticket: BuildTicket) -> list[Artifact]:
        artifacts: list[Artifact] = []
        seen: set[str] = set()
        next_path = ticket.metadata.get("next_tickets_path")
        for artifact in self.store.list_artifacts_for_ticket(ticket.id):
            if artifact.artifact_type is not ArtifactType.NEXT_TICKETS:
                continue
            if next_path and artifact.path != str(next_path):
                continue
            artifacts.append(artifact)
            seen.add(artifact.id)
        if not artifacts:
            for artifact in self.store.list_artifacts_for_ticket(ticket.id):
                if artifact.artifact_type is ArtifactType.NEXT_TICKETS and artifact.id not in seen:
                    artifacts.append(artifact)
                    seen.add(artifact.id)
        return sorted(artifacts, key=lambda item: item.created_at)

    def _artifact_item(
        self,
        artifact_id: str,
        category: str,
        execution: ExecutionResult | None = None,
    ) -> IssueEvidenceItemDTO:
        try:
            artifact = self.store.load_artifact(artifact_id)
        except FileNotFoundError:
            return self._missing_item(category, "Artifact", "artifact", artifact_id, f"Artifact {artifact_id} is missing.")
        stale_reason = self._artifact_stale_reason(artifact.metadata)
        return self._file_item(
            category=category,
            label=artifact.summary or artifact.artifact_type.value,
            ref_type=f"artifact:{artifact.artifact_type.value}",
            ref_id=artifact.id,
            path=artifact.path,
            summary=artifact.summary,
            assignment_id=execution.assignment_id if execution else None,
            execution_result_id=execution.id if execution else None,
            created_at=artifact.created_at,
            produced_by_run=execution is not None,
            validity_override="stale" if stale_reason else None,
            reason_override=stale_reason,
        )

    def _source_document_item(self, source: SourceDocument) -> IssueEvidenceItemDTO:
        return IssueEvidenceItemDTO(
            id=self._id(source.id, "source", "document"),
            category="source",
            label=f"Source: {source.title}",
            ref_type="source_document",
            ref_id=source.id,
            path_or_url=source.path_or_url,
            validity="available",
            summary=source.summary,
            excerpt=source.summary,
            created_at=source.created_at,
        )

    def _source_evidence_item(
        self,
        evidence: SourceEvidence,
        source: SourceDocument | None,
    ) -> IssueEvidenceItemDTO:
        title = source.title if source else evidence.source_document_id
        return IssueEvidenceItemDTO(
            id=self._id(evidence.id, "source", "evidence"),
            category="source",
            label=f"Claim from {title}",
            ref_type="source_evidence",
            ref_id=evidence.id,
            path_or_url=source.path_or_url if source else None,
            validity="available",
            summary=f"{evidence.claim} ({evidence.confidence:.2f})",
            excerpt=f"{evidence.locator}\nClaim: {evidence.claim}\nEvidence: {evidence.quote_or_summary}",
            created_at=str(evidence.created_at),
        )

    def _source_artifact_item(
        self,
        artifact: SourceArtifact,
        source: SourceDocument | None,
    ) -> IssueEvidenceItemDTO:
        path = self.store.source_artifact_payload_path(artifact.id)
        title = source.title if source else artifact.source_document_id
        payload = self._read_json_excerpt(path)
        return self._file_item(
            category="source",
            label=f"{artifact.artifact_type}: {title}",
            ref_type="source_artifact",
            ref_id=artifact.id,
            path=str(path),
            summary=f"{len(artifact.evidence_ids)} evidence refs.",
            excerpt_override=payload,
            created_at=str(artifact.created_at),
        )

    def _memory_record_item(self, record: MemoryRecord, path: Path) -> IssueEvidenceItemDTO:
        summary = f"{record.build_summary} {record.review_summary}".strip()
        return self._file_item(
            category="memory",
            label="Memory record",
            ref_type="memory_record",
            ref_id=record.id,
            path=str(path),
            summary=summary,
            excerpt_override="\n".join(
                part
                for part in [
                    record.decision_log_entry,
                    record.build_summary,
                    record.review_summary,
                    *record.next_actions,
                ]
                if part
            ),
            created_at=record.created_at,
        )

    def _file_item(
        self,
        *,
        category: str,
        label: str,
        ref_type: str,
        path: str,
        ref_id: str | None = None,
        summary: str = "",
        assignment_id: str | None = None,
        execution_result_id: str | None = None,
        created_at: str | None = None,
        produced_by_run: bool = False,
        excerpt_override: str | None = None,
        validity_override: str | None = None,
        reason_override: str = "",
    ) -> IssueEvidenceItemDTO:
        resolved = self._resolve_path(path)
        validity, reason = self._file_validity(resolved, produced_by_run=produced_by_run)
        if validity_override:
            validity = validity_override
            reason = reason_override
        excerpt = excerpt_override if excerpt_override is not None else self._read_excerpt(resolved, EXCERPT_LIMIT)
        return IssueEvidenceItemDTO(
            id=self._id(category, ref_type, ref_id or path),
            category=category,
            label=label,
            ref_type=ref_type,
            ref_id=ref_id,
            path_or_url=str(resolved) if resolved else path,
            validity=validity,
            reason=reason,
            summary=summary,
            excerpt=excerpt,
            assignment_id=assignment_id,
            execution_result_id=execution_result_id,
            created_at=created_at,
        )

    def _missing_item(self, category: str, label: str, ref_type: str, ref_id: str, reason: str) -> IssueEvidenceItemDTO:
        return IssueEvidenceItemDTO(
            id=self._id(category, ref_type, ref_id),
            category=category,
            label=label,
            ref_type=ref_type,
            ref_id=ref_id,
            validity="missing",
            reason=reason,
            summary=reason,
        )

    def _execution_placeholder(
        self,
        execution: ExecutionResult,
        ref_type: str,
        label: str,
        reason: str,
    ) -> IssueEvidenceItemDTO:
        return IssueEvidenceItemDTO(
            id=self._id(execution.id, "execution", ref_type, "missing"),
            category="execution",
            label=label,
            ref_type=ref_type,
            ref_id=execution.id,
            validity="missing" if execution.blocked else "not_run",
            reason=reason,
            summary=reason,
            assignment_id=execution.assignment_id,
            execution_result_id=execution.id,
            created_at=execution.ended_at,
        )

    def _full_content(self, item: IssueEvidenceItemDTO) -> str:
        if item.path_or_url and not item.path_or_url.startswith(("http://", "https://")):
            return self._read_excerpt(self._resolve_path(item.path_or_url), DETAIL_LIMIT) or item.excerpt
        return item.excerpt

    def _read_json_excerpt(self, path: Path) -> str:
        if not self._is_safe_read_path(path):
            return ""
        try:
            if path.stat().st_size > JSON_PARSE_LIMIT:
                return self._read_excerpt(path, EXCERPT_LIMIT)
            data = json.loads(self._read_limited_text(path, JSON_PARSE_LIMIT))
        except (OSError, json.JSONDecodeError):
            return self._read_excerpt(path, EXCERPT_LIMIT)
        return self._limit(json.dumps(data, ensure_ascii=False, indent=2), EXCERPT_LIMIT)

    def _read_excerpt(self, path: Path | None, limit: int) -> str:
        if path is None or not path.exists() or not path.is_file():
            return ""
        if not self._is_safe_read_path(path):
            return ""
        try:
            return self._limit(self._read_limited_text(path, limit), limit)
        except OSError:
            return ""

    def _read_limited_text(self, path: Path, limit: int) -> str:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return handle.read(limit + 1)

    def _resolve_path(self, path: str) -> Path | None:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = self.store.base / candidate
        return candidate

    def _file_validity(self, path: Path | None, *, produced_by_run: bool = False) -> tuple[str, str]:
        if path is None or not path.exists():
            return "missing", "The referenced artifact file does not exist."
        if not self._is_safe_read_path(path):
            return "missing", "The evidence viewer only opens files inside the local Ariadne store."
        if not path.is_file():
            return "missing", "The referenced artifact path is not a readable file."
        try:
            if path.stat().st_size == 0:
                return "empty", "The referenced artifact file is empty."
        except OSError:
            return "missing", "The referenced artifact file cannot be inspected."
        return ("produced_by_run" if produced_by_run else "available"), ""

    def _is_safe_read_path(self, path: Path) -> bool:
        try:
            return path.resolve(strict=False).is_relative_to(self.store.base.resolve(strict=False))
        except OSError:
            return False

    def _values(self, ticket: BuildTicket, *keys: str) -> list[str]:
        values: list[str] = []
        for key in keys:
            value = ticket.metadata.get(key)
            if isinstance(value, str) and value:
                values.append(value)
            elif isinstance(value, list):
                values.extend(str(item) for item in value if item)
        return values

    def _try_source_document(self, source_id: str) -> SourceDocument | None:
        try:
            return self.store.load_source_document(source_id)
        except FileNotFoundError:
            return None

    def _assignment_for_packet(self, assignments: list[TicketAssignment], packet_id: str) -> str | None:
        for assignment in assignments:
            if assignment.metadata.get("handoff_packet_id") == packet_id:
                return assignment.id
        return None

    def _assignment_for_route(self, assignments: list[TicketAssignment], route_id: str) -> str | None:
        for assignment in assignments:
            if assignment.metadata.get("route_decision_id") == route_id:
                return assignment.id
        return None

    def _route_summary(self, route: RouteDecision) -> str:
        return (
            f"{route.selected_agent_name or route.selected_agent_id or 'agent'} -> "
            f"{route.backend_name}; allowed skills: {', '.join(route.skill_refs) or 'none'}"
        )

    def _artifact_stale_reason(self, metadata: dict[str, object]) -> str:
        if metadata.get("stale") is True:
            return str(metadata.get("stale_reason") or "Artifact metadata marks this evidence as stale.")
        if metadata.get("evidence_packet_stale") is True:
            return str(metadata.get("stale_reason") or "The evidence packet is stale.")
        superseded_by = metadata.get("superseded_by_ref") or metadata.get("superseded_by_artifact_id")
        if superseded_by:
            return f"This artifact was superseded by {superseded_by}."
        return ""

    def _id(self, *parts: object) -> str:
        return stable_id("issue_evidence", *parts)

    def _limit(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[: limit - 1].rstrip() + "…"
