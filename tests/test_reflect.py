from __future__ import annotations

from pathlib import Path

from ariadne_ltb.knowledge.reflect import reflect_on_run
from ariadne_ltb.knowledge.store import ProjectKnowledgeStore
from ariadne_ltb.models import (
    AgentRun,
    AgentRunStatus,
    BuildTicket,
    FailureReason,
    ReviewReport,
    ReviewVerdict,
)
from ariadne_ltb.storage import AriadneStore


def test_reflect_on_blocked_run_writes_outcome_and_blocker_learning(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = BuildTicket(
        id="ticket_1",
        key="MCA-001",
        title="Bootstrap",
        description="Bootstrap target.",
        source_type="note",
        source_ref="memory://test",
        metadata={"target_project_id": "project_1"},
    )
    store.save_ticket(ticket)
    run = AgentRun(
        id="run_1",
        ticket_id=ticket.id,
        agent_name="Codex",
        agent_role="execution",
        input_summary="Run it.",
    ).mark_running().mark_finished(
        AgentRunStatus.BLOCKED,
        output_summary="Tests failed.",
        failure_reason=FailureReason.TEST_FAILED,
    )
    store.save_run(run)

    reflect_on_run(store, run=run)
    reflect_on_run(store, run=run)

    knowledge = ProjectKnowledgeStore(store, "project_1")
    outcomes = knowledge.load_outcomes_log()
    assert len(outcomes.entries) == 1
    assert outcomes.entries[0].blocker_reason == "test_failed"
    learning = knowledge.list_blocker_learnings()[0]
    assert learning.blocker_reason == "test_failed"
    assert learning.seen_in_ticket_keys == ["MCA-001"]


def test_reflect_merges_execution_and_review_into_single_entry(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = BuildTicket(
        id="ticket_1",
        key="MCA-001",
        title="Bootstrap",
        description="Bootstrap target.",
        source_type="note",
        source_ref="memory://test",
        metadata={"target_project_id": "project_1"},
    )
    store.save_ticket(ticket)
    execution_run = AgentRun(
        id="run_execution",
        ticket_id=ticket.id,
        agent_name="Codex",
        agent_role="execution",
        input_summary="Run it.",
    ).mark_running().mark_finished(
        AgentRunStatus.BLOCKED,
        output_summary="Tests failed.",
        failure_reason=FailureReason.TEST_FAILED,
    )
    review_run = AgentRun(
        id="run_review",
        ticket_id=ticket.id,
        agent_name="Reviewer",
        agent_role="reviewer",
        input_summary="Review it.",
    ).mark_running().mark_finished(
        AgentRunStatus.SUCCEEDED,
        output_summary="Reviewer passed.",
    )
    review = ReviewReport(id="review_1", ticket_id=ticket.id, verdict=ReviewVerdict.PASS)
    store.save_run(execution_run)
    store.save_run(review_run)
    store.save_review_report(review)

    reflect_on_run(store, run=execution_run)
    reflect_on_run(store, run=review_run, review=review)

    outcomes = ProjectKnowledgeStore(store, "project_1").load_outcomes_log()
    assert len(outcomes.entries) == 1
    assert outcomes.entries[0].blocker_reason == "test_failed"
    assert outcomes.entries[0].review_verdict == "pass"
