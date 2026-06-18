from __future__ import annotations

import json
from pathlib import Path

from ariadne_ltb.board import export_board
from ariadne_ltb.demo import run_demo
from ariadne_ltb.models import AgentRunStatus, ArtifactType, ReviewVerdict, TicketStatus
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_NOTE = ROOT / "examples" / "multica_research_note.md"


def test_demo_pipeline_creates_ticket_runs_and_required_artifacts(tmp_path: Path) -> None:
    result = run_demo(root=tmp_path, source_path=SOURCE_NOTE)
    store = AriadneStore(tmp_path)
    ticket = store.load_ticket(result.ticket_id)

    assert ticket.key == "ARI-001"
    assert ticket.status is TicketStatus.DONE
    assert len(ticket.agent_run_ids) == 8
    assert all(store.load_run(run_id).status is AgentRunStatus.SUCCEEDED for run_id in ticket.agent_run_ids)

    artifacts = [store.load_artifact(artifact_id) for artifact_id in ticket.artifact_ids]
    artifact_types = {artifact.artifact_type for artifact in artifacts}
    assert ArtifactType.BUILD_PACKET in artifact_types
    assert ArtifactType.CODEX_HANDOFF in artifact_types
    assert ArtifactType.DRY_RUN_EXECUTION in artifact_types
    assert ArtifactType.REVIEW_REPORT in artifact_types
    assert ArtifactType.FEISHU_WRITE_PLAN in artifact_types

    packet_path = next(artifact.path for artifact in artifacts if artifact.artifact_type is ArtifactType.BUILD_PACKET)
    packet = json.loads(Path(packet_path).read_text(encoding="utf-8"))
    assert packet["build_decision"] == "code_task"
    assert packet["evidence"]
    packet_text = Path(packet_path).read_text(encoding="utf-8")
    assert "Feishu write plan is dry-run only" not in packet_text
    assert "gated real write path" in packet_text

    lead_path = next(artifact.path for artifact in artifacts if Path(artifact.path).name == "lead_routing.md")
    lead_routing = Path(lead_path).read_text(encoding="utf-8")
    assert "Execution backend remains dry-run only" not in lead_routing
    assert "No external APIs" not in lead_routing
    normalized_lead_routing = " ".join(lead_routing.split())
    assert "Codex and Claude Code are production backends" in normalized_lead_routing

    review_path = next(artifact.path for artifact in artifacts if artifact.artifact_type is ArtifactType.REVIEW_REPORT)
    review = json.loads(Path(review_path).read_text(encoding="utf-8"))
    assert review["verdict"] == ReviewVerdict.PASS.value

    feishu_path = next(artifact.path for artifact in artifacts if artifact.artifact_type is ArtifactType.FEISHU_WRITE_PLAN)
    feishu = json.loads(Path(feishu_path).read_text(encoding="utf-8"))
    assert feishu["dry_run"] is True
    assert feishu["proposed_tasks"]


def test_demo_is_idempotent_for_ticket_identity_without_duplicate_runs(tmp_path: Path) -> None:
    first = run_demo(root=tmp_path, source_path=SOURCE_NOTE)
    second = run_demo(root=tmp_path, source_path=SOURCE_NOTE)
    store = AriadneStore(tmp_path)
    ticket = store.load_ticket(second.ticket_id)

    assert first.ticket_id == second.ticket_id
    assert len(ticket.agent_run_ids) == 8


def test_board_export_shows_ticket_timeline_and_review(tmp_path: Path) -> None:
    result = run_demo(root=tmp_path, source_path=SOURCE_NOTE)
    board_path = export_board(AriadneStore(tmp_path))

    board = board_path.read_text(encoding="utf-8")
    assert result.ticket_id in board
    assert "Agent Run Timeline" in board
    assert "Review Verdict" in board
    assert "Feishu Write Plan" in board


def test_reviewer_is_conservative_when_required_artifacts_are_missing(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    result = run_demo(root=tmp_path, source_path=SOURCE_NOTE)
    ticket = store.load_ticket(result.ticket_id)
    ticket.artifact_ids = [
        artifact_id
        for artifact_id in ticket.artifact_ids
        if store.load_artifact(artifact_id).artifact_type is not ArtifactType.CODEX_HANDOFF
    ]
    store.save_ticket(ticket)

    from ariadne_ltb.agents import ReviewerAgent
    from ariadne_ltb.runtime import RuntimeContext

    review = ReviewerAgent().evaluate(RuntimeContext(store=store, ticket=ticket, source_text=""))
    assert review.verdict is ReviewVerdict.NEEDS_FIX
    assert any("Codex handoff" in check for check in review.failed_checks)
