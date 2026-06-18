from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.board import export_board
from ariadne_ltb.cli import app
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import CommentAuthorType, CommentKind
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURE = ROOT / "examples" / "sources" / "github_tiny_cli_readme.md"


def _seed_legacy_comment(root: Path) -> AriadneStore:
    store = AriadneStore(root)
    [ticket] = ingest_sources(store, [SOURCE_FIXTURE])
    store.add_comment(
        ticket,
        CommentAuthorType.AGENT,
        "Memory",
        CommentKind.MEMORY,
        "Memory wrote decision log and Feishu dry-run plan.",
    )
    return store


def test_ticket_comments_normalize_legacy_feishu_dry_run_wording(tmp_path: Path) -> None:
    _seed_legacy_comment(tmp_path)

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "ticket", "comments", "ARI-001"])

    assert result.exit_code == 0, result.output
    assert "Feishu preview plan" in result.output
    assert "Feishu dry-run plan" not in result.output


def test_board_normalizes_legacy_feishu_dry_run_wording(tmp_path: Path) -> None:
    store = _seed_legacy_comment(tmp_path)

    board_path = export_board(store)
    board = board_path.read_text(encoding="utf-8")

    assert "Feishu preview plan" in board
    assert "Feishu dry-run plan" not in board
