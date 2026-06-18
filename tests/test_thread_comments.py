from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.board import export_board
from ariadne_ltb.cli import app
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import CommentAuthorType, CommentKind, TicketComment, stable_id
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def _ticket(store: AriadneStore):
    return ingest_sources(store, SOURCE_FIXTURES)[2]


def test_ticket_comment_loads_legacy_json_without_thread_fields() -> None:
    payload = {
        "id": "comment_legacy",
        "ticket_id": "ticket_demo",
        "ticket_key": "ARI-001",
        "author_type": "human",
        "author": "human",
        "kind": "comment",
        "body": "legacy comment",
        "payload_ref": None,
        "created_at": "2026-06-17T00:00:00Z",
    }

    comment = TicketComment.model_validate_json(json.dumps(payload))

    assert comment.parent_comment_id is None
    assert comment.thread_id == comment.id


def test_store_comment_threads_roots_since_and_tail(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = _ticket(store)

    root = store.add_comment(
        ticket,
        CommentAuthorType.HUMAN,
        "human",
        CommentKind.COMMENT,
        "root",
    )
    reply = store.add_comment(
        ticket,
        CommentAuthorType.HUMAN,
        "human",
        CommentKind.COMMENT,
        "reply",
        parent_comment_id=root.id,
    )
    nested = store.add_comment(
        ticket,
        CommentAuthorType.HUMAN,
        "human",
        CommentKind.COMMENT,
        "nested",
        parent_comment_id=reply.id,
    )
    older = TicketComment(
        id=stable_id("comment", ticket.id, "older"),
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        author_type=CommentAuthorType.SYSTEM,
        author="Ariadne",
        kind=CommentKind.COMMENT,
        body="older",
        created_at="2026-01-01T00:00:00Z",
    )
    store.append_comment(older)

    assert reply.parent_comment_id == root.id
    assert reply.thread_id == root.thread_id
    assert nested.thread_id == root.thread_id
    assert [comment.id for comment in store.list_comment_roots(ticket.id)] == [root.id, older.id]
    assert [comment.body for comment in store.list_comment_thread(ticket.id, reply.id)] == [
        "root",
        "reply",
        "nested",
    ]
    assert [comment.body for comment in store.list_comments(ticket.id, tail=1)] == ["older"]
    assert "older" not in [comment.body for comment in store.list_comments(ticket.id, since="2026-06-01T00:00:00Z")]


def test_cli_comment_threads_roots_recent_tail_and_thread(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = _ticket(store)
    runner = CliRunner()

    root = runner.invoke(app, ["--root", str(tmp_path), "ticket", "comment", ticket.key, "root"])
    assert root.exit_code == 0, root.output
    root_id = root.output.split("comment: ", 1)[1].splitlines()[0]
    thread_id = root.output.split("thread: ", 1)[1].splitlines()[0]
    reply = runner.invoke(
        app,
        ["--root", str(tmp_path), "ticket", "comment", ticket.key, "reply", "--reply-to", root_id],
    )
    assert reply.exit_code == 0, reply.output
    assert f"thread: {thread_id}" in reply.output

    roots = runner.invoke(app, ["--root", str(tmp_path), "ticket", "comments", ticket.key, "--roots"])
    assert roots.exit_code == 0, roots.output
    assert "root" in roots.output
    assert "reply" not in roots.output

    thread = runner.invoke(app, ["--root", str(tmp_path), "ticket", "comments", ticket.key, "--thread", root_id])
    assert thread.exit_code == 0, thread.output
    assert "root" in thread.output
    assert "reply" in thread.output
    assert f"thread={thread_id}" in thread.output

    tail = runner.invoke(app, ["--root", str(tmp_path), "ticket", "comments", ticket.key, "--tail", "1"])
    assert tail.exit_code == 0, tail.output
    assert "reply" in tail.output
    assert "root" not in tail.output

    recent = runner.invoke(app, ["--root", str(tmp_path), "ticket", "comments", ticket.key, "--recent", "1"])
    assert recent.exit_code == 0, recent.output
    assert "comments=2" in recent.output
    assert "root=root" in recent.output

    invalid = runner.invoke(
        app,
        ["--root", str(tmp_path), "ticket", "comments", ticket.key, "--recent", "1", "--tail", "1"],
    )
    assert invalid.exit_code == 2
    assert "cannot be combined" in invalid.output


def test_board_shows_thread_summaries_and_comment_ids(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = _ticket(store)
    root = store.add_comment(
        ticket,
        CommentAuthorType.HUMAN,
        "human",
        CommentKind.COMMENT,
        "root body",
    )
    reply = store.add_comment(
        ticket,
        CommentAuthorType.HUMAN,
        "human",
        CommentKind.COMMENT,
        "latest reply body",
        parent_comment_id=root.id,
    )

    board = export_board(store).read_text(encoding="utf-8")

    assert "### Comment Threads" in board
    assert f"thread=`{root.thread_id}`" in board
    assert f"parent=`{root.id}`" in board
    assert "comments=2" in board
    assert "root body" in board
    assert "latest reply body" in board
    assert reply.id not in board or "parent=" in board


def test_daemon_assignment_comments_share_assignment_thread(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    _ticket(store)
    runner = CliRunner()
    assign = runner.invoke(app, ["--root", str(tmp_path), "ticket", "assign", "ARI-003", "--to", "fake-codex"])
    assert assign.exit_code == 0, assign.output
    assignment_id = assign.output.split("Assignment created: ", 1)[1].splitlines()[0]

    run = runner.invoke(app, ["--root", str(tmp_path), "daemon", "run-once"])
    assert run.exit_code == 0, run.output
    ticket = store.resolve_ticket("ARI-003")
    comments = store.list_comments(ticket.id)
    threaded = [comment for comment in comments if comment.thread_id == assignment_id]

    assert len(threaded) >= 4
    assert any(comment.kind is CommentKind.ASSIGNMENT for comment in threaded)
    assert any(comment.kind is CommentKind.HANDOFF for comment in threaded)
    assert any(comment.kind is CommentKind.REVIEW for comment in threaded)
    assert any(comment.kind is CommentKind.MEMORY for comment in threaded)
