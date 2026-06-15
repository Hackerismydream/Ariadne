from __future__ import annotations

from pathlib import Path

from ariadne_ltb.ingest import ingest_sources, source_document_from_path
from ariadne_ltb.models import BuildDecision
from ariadne_ltb.planner import DeterministicPlanner, LLMPlanner
from ariadne_ltb.storage import AriadneStore


def test_arbitrary_markdown_extracts_title_headings_actions_and_evidence(tmp_path: Path) -> None:
    source_path = tmp_path / "generic.md"
    source_path.write_text(
        "# Add Runtime Search\n\n"
        "## Problem\n\n"
        "We should implement memory search before planning.\n\n"
        "## Acceptance\n\n"
        "- add CLI search\n"
        "- evaluate results\n",
        encoding="utf-8",
    )

    source = source_document_from_path(source_path)

    assert source.title == "Add Runtime Search"
    assert source.metadata["headings"] == ["Problem", "Acceptance"]
    assert "implement" in source.metadata["action_verbs"]
    assert len(source.metadata["evidence_snippets"]) >= 2


def test_deterministic_planner_scores_build_packet_quality(tmp_path: Path) -> None:
    source_path = tmp_path / "feature.md"
    source_path.write_text(
        "# CLI Feature\n\nImplementation note: add CLI command and tests for a feature.\n",
        encoding="utf-8",
    )
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [source_path])[0]
    result = DeterministicPlanner().plan_ticket(store, ticket)
    packet = store.load_build_packet(result.build_packet_id)

    assert packet.build_decision is BuildDecision.CODE_TASK
    quality = packet.metadata["quality"]
    assert 0 <= quality["overall_quality"] <= 1
    assert quality["evidence_coverage_score"] > 0
    assert quality["acceptance_criteria_score"] > 0


def test_llm_planner_invalid_json_writes_error_artifact(tmp_path: Path) -> None:
    class BadClient:
        def complete_json(self, prompt: str, schema_name: str) -> dict:
            return {"source_summary": "missing required fields"}

    source_path = tmp_path / "llm.md"
    source_path.write_text("# LLM Note\n\nBuild a feature.\n", encoding="utf-8")
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [source_path])[0]

    result = LLMPlanner(client=BadClient()).plan_ticket(store, ticket)

    assert result.succeeded is False
    assert result.error_artifact_path
    assert Path(result.error_artifact_path).exists()


def test_self_improvement_source_generates_code_task_or_architecture_change(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    source = root / "examples" / "sources" / "ariadne_self_improvement_note.md"
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [source])[0]
    packet = store.load_build_packet(ticket.build_packet_id)

    assert packet.build_decision in {BuildDecision.CODE_TASK, BuildDecision.ARCHITECTURE_CHANGE}
    assert len(packet.evidence) >= 2
