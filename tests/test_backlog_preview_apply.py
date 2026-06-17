from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.backlog import generate_source_backlog_preview, ticket_backlog_fingerprint
from ariadne_ltb.board import export_board
from ariadne_ltb.cli import app
from ariadne_ltb.models import BacklogOperationType, BuildTicket, TicketStatus
from ariadne_ltb.storage import AriadneStore


def test_source_backlog_preview_is_stable_and_does_not_mutate_tickets(tmp_path: Path) -> None:
    source = _source(tmp_path, "source.md", "# Source\n\nBuild a small feature.\n")
    store = AriadneStore(tmp_path)

    first = generate_source_backlog_preview(store, [source])
    second = generate_source_backlog_preview(store, [source])

    assert first.id == second.id
    assert first.idempotency_key == second.idempotency_key
    assert len(store.list_backlog_previews()) == 1
    assert store.list_tickets() == []
    assert first.operations[0].operation_type is BacklogOperationType.ADD_TICKET


def test_backlog_apply_is_idempotent_and_auditable(tmp_path: Path) -> None:
    source = _source(tmp_path, "source.md", "# Source\n\nBuild a small feature.\n")
    runner = CliRunner()

    preview = runner.invoke(app, ["--root", str(tmp_path), "backlog", "preview", "--from-source", str(source)])
    preview_id = _line_value(preview.output, "preview:")
    first_apply = runner.invoke(app, ["--root", str(tmp_path), "backlog", "apply", preview_id])
    second_apply = runner.invoke(app, ["--root", str(tmp_path), "backlog", "apply", preview_id])
    store = AriadneStore(tmp_path)
    preview_record = store.load_backlog_preview(preview_id)

    assert preview.exit_code == 0, preview.output
    assert first_apply.exit_code == 0, first_apply.output
    assert second_apply.exit_code == 0, second_apply.output
    assert "already applied" in second_apply.output
    assert len(store.list_tickets()) == 1
    assert len(store.list_backlog_updates()) == 1
    assert preview_record.applied_update_id == store.list_backlog_updates()[0].id


def test_stale_backlog_preview_apply_is_rejected(tmp_path: Path) -> None:
    source = _source(tmp_path, "source.md", "# Source\n\nBuild a small feature.\n")
    store = AriadneStore(tmp_path)
    preview = generate_source_backlog_preview(store, [source])
    store.save_ticket(_ticket_for_stale_state())

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "backlog", "apply", preview.id])

    assert result.exit_code == 2
    assert "stale_preview" in result.output
    assert len(store.list_backlog_updates()) == 0


def test_backlog_preview_board_shows_pending_and_applied_operations(tmp_path: Path) -> None:
    source = _source(tmp_path, "source.md", "# Source\n\nBuild a small feature.\n")
    store = AriadneStore(tmp_path)
    preview = generate_source_backlog_preview(store, [source])
    pending_board = export_board(store).read_text(encoding="utf-8")
    applied = CliRunner().invoke(app, ["--root", str(tmp_path), "backlog", "apply", preview.id])
    applied_board = export_board(store).read_text(encoding="utf-8")

    assert applied.exit_code == 0, applied.output
    assert "## Backlog Previews" in pending_board
    assert preview.id in pending_board
    assert "Status `pending`" in pending_board
    assert "Operations `1`" in pending_board
    assert "Status `applied`" in applied_board
    assert "Applied update:" in applied_board


def test_multi_source_preview_allocates_unique_keys_when_backlog_has_gap(tmp_path: Path) -> None:
    first = _ticket_for_stale_state().model_copy(update={"key": "ARI-001"})
    third = _ticket_for_stale_state().model_copy(update={"id": "ticket_third", "key": "ARI-003"})
    source_a = _source(tmp_path, "a.md", "# A\n\nBuild A.\n")
    source_b = _source(tmp_path, "b.md", "# B\n\nBuild B.\n")
    store = AriadneStore(tmp_path)
    store.save_ticket(first)
    store.save_ticket(third)

    preview = generate_source_backlog_preview(store, [source_a, source_b])
    keys = [operation.ticket_key for operation in preview.operations]

    assert len(keys) == len(set(keys))
    assert keys == ["ARI-002", "ARI-004"]
    assert not preview.conflicts


def test_backlog_fingerprint_tracks_ticket_state(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    before = ticket_backlog_fingerprint(store)
    store.save_ticket(_ticket_for_stale_state())

    assert ticket_backlog_fingerprint(store) != before


def _source(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def _ticket_for_stale_state() -> BuildTicket:
    return BuildTicket(
        id="ticket_external",
        key="ARI-999",
        title="External state change",
        description="Creates a stale preview fingerprint.",
        source_type="note",
        source_ref="manual",
        status=TicketStatus.PLANNING,
    )


def _line_value(output: str, prefix: str) -> str:
    for line in output.splitlines():
        if line.startswith(prefix):
            return line.split(":", maxsplit=1)[1].strip()
    raise AssertionError(output)
