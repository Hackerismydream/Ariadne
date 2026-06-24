from __future__ import annotations

from ariadne_ltb.knowledge.models import (
    BlockerLearning,
    ClaimWithEvidence,
    ContradictionRecord,
    OutcomeEntry,
    OutcomesLog,
    ProjectPurpose,
    SourceInsight,
    SynthesisTheme,
)


def test_project_knowledge_models_round_trip() -> None:
    purpose = ProjectPurpose(
        project_id="project_1",
        title="Mini Code Agent",
        one_line="Build a useful local code agent.",
        why_this_exists="AI builders need a compact inspectable coding agent.",
        target_users=["AI builder"],
        success_signals=["CLI can solve a toy issue"],
        out_of_scope=["hosted SaaS"],
        constraints=["local-first"],
    )
    claim = ClaimWithEvidence(
        claim="Agents need an action-observation loop.",
        locator="README.md",
        confidence=0.9,
        source_document_id="source_1",
    )
    insight = SourceInsight(
        id="insight_1",
        project_id=purpose.project_id,
        source_document_id="source_1",
        summary="Reference repo exposes an agent loop.",
        key_claims=[claim],
        reusable_patterns=["loop"],
        risks=["unsafe shell"],
        last_ingest_cycle="cycle_1",
    )
    theme = SynthesisTheme(
        id="theme_1",
        project_id=purpose.project_id,
        label="Agent loop",
        contributing_source_ids=["source_1"],
        claims=["Use action-observation loop"],
        priority_signal="high",
        affected_modules=["mini_code_agent/agent_loop.py"],
        last_updated_cycle="cycle_1",
    )
    contradiction = ContradictionRecord(
        id="contradiction_1",
        project_id=purpose.project_id,
        summary="Shell access safety differs.",
        competing_claims=[claim],
        affected_theme_ids=[theme.id],
    )
    blocker = BlockerLearning(
        id="blocker_1",
        project_id=purpose.project_id,
        blocker_reason="test_failed",
        failure_pattern="tests fail after file writes",
        mitigation="run pytest before review",
        seen_in_ticket_keys=["MCA-001"],
    )
    outcomes = OutcomesLog(
        project_id=purpose.project_id,
        entries=[
            OutcomeEntry(
                ticket_key="MCA-001",
                ticket_title="Bootstrap",
                status="done",
                review_verdict="pass",
                learnings=["run:run_1"],
            )
        ],
    )

    for model in [purpose, insight, theme, contradiction, blocker, outcomes]:
        assert type(model).model_validate_json(model.model_dump_json()) == model

