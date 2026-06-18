from __future__ import annotations

from pathlib import Path

from ariadne_ltb.application.comments import CommentService
from ariadne_ltb.application.dtos import CreateCommentInput
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_comment_service_persists_human_comment_and_replays_idempotency(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    service = CommentService(store)

    first = service.add_human_comment(
        "ARI-003",
        CreateCommentInput(body="needs clearer progress", idempotency_key="comment-1"),
    )
    second = service.add_human_comment(
        "ARI-003",
        CreateCommentInput(body="duplicate should not persist", idempotency_key="comment-1"),
    )

    comments = store.list_comments(first.ticket_id)
    assert first.id == second.id
    assert len(comments) == 1
    assert comments[0].author == "human"
    assert comments[0].body == "needs clearer progress"


def test_comment_service_links_assignment_thread(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    comment = CommentService(store).add_human_comment(
        "ARI-003",
        CreateCommentInput(body="run follow-up", assignment_id="assignment_1", idempotency_key="comment-2"),
    )

    stored = store.find_comment(comment.ticket_id, comment.id)

    assert stored.thread_id == "assignment_1"
    assert stored.payload_ref == "assignment_1"
