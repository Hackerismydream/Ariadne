from __future__ import annotations

from pathlib import Path

from ariadne_ltb.application.assign_ticket import AssignTicketService
from ariadne_ltb.application.comments import CommentService
from ariadne_ltb.application.dtos import AssignTicketInput, CreateCommentInput
from ariadne_ltb.application.run_events import RunEventService
from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_assignment_events_include_assignment_and_threaded_comment(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = ensure_demo_target_project(tmp_path)
    project = TargetProjectRegistry(store).register(target, "Demo Target")
    assigned = AssignTicketService(store).assign(
        "ARI-003",
        AssignTicketInput(
            assignee_id="build-team",
            assignee_kind="build_team",
            backend_name="fake-codex",
            runtime_profile="deterministic",
            target_project_id=project.id,
            idempotency_key="assign-timeline",
        ),
        source="test",
    )
    CommentService(store).add_human_comment(
        "ARI-003",
        CreateCommentInput(
            body="please show progress",
            assignment_id=assigned.assignment.id,
            idempotency_key="comment-timeline",
        ),
    )

    events = RunEventService(store).assignment_events(assigned.assignment.id).events

    assert [event.cursor for event in events] == sorted(event.cursor for event in events)
    assert any(event.source == "assignment" for event in events)
    assert any(event.source == "comment" and event.summary == "please show progress" for event in events)
    assert "confirmation_token" not in "".join(event.model_dump_json() for event in events)
