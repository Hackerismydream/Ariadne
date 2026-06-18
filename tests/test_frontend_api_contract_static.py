from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_TYPES = ROOT / "frontend" / "ariadne-workbench" / "src" / "shared" / "api" / "types.ts"
APP = ROOT / "frontend" / "ariadne-workbench" / "src" / "App.tsx"
RUNTIME_LIB = ROOT / "frontend" / "ariadne-workbench" / "src" / "entities" / "runtime" / "lib.ts"


def test_frontend_request_types_do_not_expose_forbidden_fields() -> None:
    text = API_TYPES.read_text(encoding="utf-8")
    assign_block = text.split("export type AssignTicketRequest", 1)[1].split("};", 1)[0]
    run_block = text.split("export type RunAssignmentRequest", 1)[1].split("};", 1)[0]

    for forbidden in [
        "planner_name",
        "agent_runtime",
        "backlog_planner_name",
        "runtime_id",
        "backlog_planner",
        "target_repo_path",
        "command",
        "shell",
        "confirm_execution",
    ]:
        assert forbidden not in assign_block
        assert forbidden not in run_block
    assert "confirmation_token" in run_block


def test_frontend_has_planned_feature_and_entity_modules() -> None:
    required = [
        "entities/runtime/model.ts",
        "entities/runtime/lib.ts",
        "entities/assignment/model.ts",
        "entities/ticket/model.ts",
        "entities/target-project/model.ts",
        "features/assign-ticket/api.ts",
        "features/run-assignment/api.ts",
        "features/watch-run-events/api.ts",
        "features/add-ticket-comment/api.ts",
    ]
    for relative in required:
        assert (ROOT / "frontend" / "ariadne-workbench" / "src" / relative).exists()


def test_frontend_runtime_filter_excludes_fallback_backends() -> None:
    text = RUNTIME_LIB.read_text(encoding="utf-8")

    assert "fallbackOnly" in text
    assert 'runtime.backend === "shell"' in text


def test_frontend_wires_assign_run_watch_comment() -> None:
    text = APP.read_text(encoding="utf-8")

    assert "assignTicket(" in text
    assert "runAssignment(" in text
    assert "getAssignmentEvents(" in text
    assert "addTicketComment(" in text
    assert "readOnly" in text


def test_frontend_product_assign_uses_selected_backend_agent_not_build_team() -> None:
    text = APP.read_text(encoding="utf-8")
    inspector_block = text.split("function TicketInspector", 1)[1]

    assert 'assignee_kind: "agent"' in inspector_block
    assert "assignee_id: productRuntime.backend" in inspector_block
    assert 'assignee_id: "build-team"' not in inspector_block


def test_frontend_mutations_refresh_the_current_ticket() -> None:
    text = APP.read_text(encoding="utf-8")

    assert "async function refreshWorkbenchData(preferredTicketRef?: string)" in text
    assert "const preferredTicket = findTicketByRef(result.data.tickets, preferredTicketRef)" in text
    assert "await onRefresh(ticket.key)" in text


def test_frontend_assignment_events_show_recent_progress() -> None:
    text = APP.read_text(encoding="utf-8")

    assert "assignmentEvents.map((event)" in text
    assert "assignmentEvents.slice(-12)" not in text
    assert "assignmentEvents.slice(0, 6)" not in text
