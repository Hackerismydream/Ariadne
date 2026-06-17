from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ariadne_ltb.storage import AriadneStore


@dataclass(frozen=True)
class LocalSearchHit:
    kind: str
    title: str
    snippet: str
    source_ref: str
    score: float
    matched_terms: list[str]
    ticket_key: str | None = None


@dataclass(frozen=True)
class _SearchDocument:
    kind: str
    title: str
    text: str
    source_ref: str
    ticket_key: str | None = None


def search_local_evidence(store: AriadneStore, query: str, limit: int = 20) -> list[LocalSearchHit]:
    query_terms = _terms(query)
    if not query_terms:
        return []

    hits: list[LocalSearchHit] = []
    for document in _documents(store):
        haystack_terms = _terms(f"{document.title}\n{document.text}")
        matched = sorted(set(query_terms) & set(haystack_terms))
        if not matched:
            continue
        score = _score_terms(query_terms, haystack_terms, matched)
        hits.append(
            LocalSearchHit(
                kind=document.kind,
                title=document.title,
                snippet=_snippet(document.text, matched),
                source_ref=document.source_ref,
                score=score,
                matched_terms=matched,
                ticket_key=document.ticket_key,
            )
        )

    return sorted(hits, key=lambda hit: (-hit.score, hit.kind, hit.title, hit.source_ref))[:limit]


def _documents(store: AriadneStore) -> list[_SearchDocument]:
    docs: list[_SearchDocument] = []
    tickets = store.list_tickets()
    ticket_key_by_id = {ticket.id: ticket.key for ticket in tickets}

    for ticket in tickets:
        docs.append(
            _SearchDocument(
                kind="ticket",
                title=f"{ticket.key} {ticket.title}",
                text=" ".join(
                    [
                        ticket.description,
                        ticket.status.value,
                        ticket.source_type,
                        ticket.source_ref,
                    ]
                ),
                source_ref=str(store.tickets_dir / f"{ticket.id}.json"),
                ticket_key=ticket.key,
            )
        )
        for comment in store.list_comments(ticket.id):
            docs.append(
                _SearchDocument(
                    kind="comment",
                    title=f"{comment.ticket_key} {comment.kind.value} by {comment.author}",
                    text=comment.body,
                    source_ref=str(store.comments_dir / f"{ticket.id}.jsonl"),
                    ticket_key=comment.ticket_key,
                )
            )
        for artifact in store.list_artifacts_for_ticket(ticket.id):
            docs.append(
                _SearchDocument(
                    kind="artifact",
                    title=f"{ticket.key} {artifact.artifact_type.value} {Path(artifact.path).name}",
                    text=_safe_read_artifact(store, artifact.id),
                    source_ref=artifact.path,
                    ticket_key=ticket.key,
                )
            )

    for record in store.list_memory_records():
        docs.append(
            _SearchDocument(
                kind="memory",
                title=record.title,
                text=" ".join(
                    [
                        record.decision_log_entry,
                        record.build_summary,
                        record.review_summary,
                        " ".join(record.next_actions),
                    ]
                ),
                source_ref=str(store.memory_dir / "tickets" / f"{record.ticket_id}.json"),
                ticket_key=ticket_key_by_id.get(record.ticket_id),
            )
        )

    for review in store.list_review_reports():
        docs.append(
            _SearchDocument(
                kind="review",
                title=f"{ticket_key_by_id.get(review.ticket_id, review.ticket_id)} review {review.verdict.value}",
                text=" ".join(
                    [
                        " ".join(review.passed_checks),
                        " ".join(review.failed_checks),
                        " ".join(review.warnings),
                        " ".join(review.required_fixes),
                        " ".join(reason.value for reason in review.failure_reasons),
                    ]
                ),
                source_ref=str(store.reviews_dir / f"{review.id}.json"),
                ticket_key=ticket_key_by_id.get(review.ticket_id),
            )
        )

    for execution in store.list_execution_results():
        docs.append(
            _SearchDocument(
                kind="execution",
                title=f"{ticket_key_by_id.get(execution.ticket_id, execution.ticket_id)} {execution.backend_name}",
                text=" ".join(
                    [
                        execution.block_reason or "",
                        execution.failure_reason.value if execution.failure_reason else "",
                        execution.provider_failure_kind or "",
                        execution.provider_failure_evidence or "",
                        execution.stdout,
                        execution.stderr,
                        execution.test_stdout,
                        execution.test_stderr,
                        " ".join(execution.changed_files),
                    ]
                ),
                source_ref=str(store.execution_results_dir / f"{execution.id}.json"),
                ticket_key=ticket_key_by_id.get(execution.ticket_id),
            )
        )

    for item in store.list_inbox_items():
        docs.append(
            _SearchDocument(
                kind="inbox",
                title=item.title,
                text=" ".join(
                    [
                        item.summary,
                        item.failure_reason.value if item.failure_reason else "",
                        item.recommended_action,
                    ]
                ),
                source_ref=item.evidence_ref or str(store.inbox_items_path),
                ticket_key=item.ticket_key,
            )
        )

    for result in store.list_feishu_write_results():
        docs.append(
            _SearchDocument(
                kind="feishu",
                title=f"{result.ticket_key} Feishu write result",
                text=" ".join(
                    [
                        result.reason or "",
                        result.failure_reason.value if result.failure_reason else "",
                        result.operation_summary,
                        result.stdout,
                        result.stderr,
                        result.document_url or "",
                    ]
                ),
                source_ref=str(store.feishu_integrations_dir / result.ticket_key / f"{result.id}.json"),
                ticket_key=result.ticket_key,
            )
        )

    for result in store.list_github_integration_results():
        docs.append(
            _SearchDocument(
                kind="github",
                title=f"{result.ticket_key} GitHub {result.operation}",
                text=" ".join(
                    [
                        result.reason or "",
                        result.failure_reason.value if result.failure_reason else "",
                        result.repo or "",
                        result.issue_url or "",
                        result.pr_url or "",
                        result.comment_url or "",
                        result.stdout,
                        result.stderr,
                    ]
                ),
                source_ref=str(store.github_integrations_dir / result.ticket_key / f"{result.id}.json"),
                ticket_key=result.ticket_key,
            )
        )

    return docs


def _safe_read_artifact(store: AriadneStore, artifact_id: str) -> str:
    try:
        artifact = store.load_artifact(artifact_id)
        return store.read_artifact_text(artifact)[:5000]
    except (OSError, ValueError):
        return ""


def _terms(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z0-9_./:-]+", text.lower())
    return [word for word in words if len(word) >= 3 and word not in _STOP_WORDS]


def _score_terms(query_terms: list[str], haystack_terms: list[str], matched: list[str]) -> float:
    coverage = len(matched) / max(len(set(query_terms)), 1)
    frequency = sum(haystack_terms.count(term) for term in matched) / max(len(haystack_terms), 1)
    return round(min(1.0, coverage * 0.85 + frequency * 2.0), 4)


def _snippet(text: str, matched: list[str]) -> str:
    if not text:
        return ""
    lowered = text.lower()
    positions = [lowered.find(term) for term in matched if term in lowered]
    start = min([position for position in positions if position >= 0], default=0)
    start = max(start - 60, 0)
    return text[start : start + 260].replace("\n", " ")


_STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "ariadne",
}
