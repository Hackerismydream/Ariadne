from __future__ import annotations

from pathlib import Path

import pytest

from ariadne_ltb.application.assign_ticket import AssignTicketService
from ariadne_ltb.application.dtos import AssignTicketInput, RunAssignmentInput
from ariadne_ltb.application.run_assignment import RunAssignmentService
from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_run_assignment_service_rejects_wrong_confirmation_token(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = TargetProjectRegistry(store).register(ensure_demo_target_project(tmp_path), "Demo Target")
    assignment = AssignTicketService(store).assign(
        "ARI-003",
        AssignTicketInput(
            assignee_id="build-team",
            backend_name="codex",
            runtime_profile="deterministic",
            target_project_id=target.id,
        ),
        source="http",
    )

    with pytest.raises(Exception, match="confirmation token"):
        RunAssignmentService(store).run(
            assignment.assignment.id,
            RunAssignmentInput(confirmation_token="wrong", timeout_seconds=30),
        )
