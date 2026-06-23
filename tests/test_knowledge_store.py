from __future__ import annotations

from pathlib import Path

from ariadne_ltb.knowledge.models import OutcomeEntry, OutcomesLog, ProjectPurpose, SourceInsight, SynthesisTheme
from ariadne_ltb.knowledge.store import ProjectKnowledgeStore
from ariadne_ltb.storage import AriadneStore


def test_project_knowledge_store_round_trip(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    knowledge = ProjectKnowledgeStore(store, "project_1")
    purpose = knowledge.save_project_purpose(
        ProjectPurpose(project_id="project_1", title="Project", one_line="Build it")
    )
    insight = knowledge.save_source_insight(
        SourceInsight(
            id="insight_1",
            project_id="project_1",
            source_document_id="source_1",
            summary="Source summary",
            last_ingest_cycle="cycle_1",
        )
    )
    theme = knowledge.save_synthesis_theme(
        SynthesisTheme(
            id="theme_1",
            project_id="project_1",
            label="Theme",
            last_updated_cycle="cycle_1",
        )
    )
    knowledge.save_outcomes_log(
        OutcomesLog(
            project_id="project_1",
            entries=[
                OutcomeEntry(ticket_key=f"T-{index}", ticket_title="Ticket", status="done")
                for index in range(25)
            ],
        )
    )

    assert knowledge.load_project_purpose().id if hasattr(purpose, "id") else purpose.project_id
    assert knowledge.source_insight_by_source_id()["source_1"] == insight
    assert knowledge.list_synthesis_themes() == [theme]
    assert len(knowledge.load_outcomes_log().entries) == 20
    assert (store.base / "knowledge" / "project_1" / "source_insights" / "insight_1.json").exists()

