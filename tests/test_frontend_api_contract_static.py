from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_TYPES = ROOT / "frontend" / "ariadne-workbench" / "src" / "shared" / "api" / "types.ts"
APP = ROOT / "frontend" / "ariadne-workbench" / "src" / "App.tsx"
DATA = ROOT / "frontend" / "ariadne-workbench" / "src" / "data.ts"
AGENT_CONTROL = ROOT / "frontend" / "ariadne-workbench" / "src" / "features" / "agent-control" / "model.ts"
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
        "features/agent-control/model.ts",
    ]
    for relative in required:
        assert (ROOT / "frontend" / "ariadne-workbench" / "src" / relative).exists()


def test_frontend_runtime_filter_excludes_fallback_backends() -> None:
    text = RUNTIME_LIB.read_text(encoding="utf-8")

    assert "fallbackOnly" in text
    assert 'runtime.backend === "shell"' in text


def test_frontend_wires_assign_run_watch_comment() -> None:
    text = AGENT_CONTROL.read_text(encoding="utf-8")

    assert "assignTicket(" in text
    assert "runAssignment(" in text
    assert "runAssignmentNow(" in text
    assert "startDaemon(" in text
    assert "stopDaemon(" in text
    assert "getAssignmentEvents(" in text
    assert "openAssignmentEventsSocket(" in text
    assert "addTicketComment(" in text
    assert "readOnly" in text


def test_frontend_product_assign_uses_selected_backend_agent_not_build_team() -> None:
    inspector_block = AGENT_CONTROL.read_text(encoding="utf-8")

    assert 'assignee_kind: "agent"' in inspector_block
    assert "assignee_id: productRuntime.backend" in inspector_block
    assert 'assignee_id: "build-team"' not in inspector_block


def test_frontend_mutations_refresh_the_current_ticket() -> None:
    text = APP.read_text(encoding="utf-8")
    control = AGENT_CONTROL.read_text(encoding="utf-8")

    assert "async function refreshWorkbenchData(preferredTicketRef?: string)" in text
    assert "const preferredTicket = findTicketByRef(result.data.tickets, preferredTicketRef)" in text
    assert "await onRefresh(ticket.key)" in control


def test_frontend_assignment_events_show_recent_progress() -> None:
    text = APP.read_text(encoding="utf-8")

    assert "assignmentEvents.map((event)" in text
    assert "assignmentEvents.slice(-12)" not in text
    assert "assignmentEvents.slice(0, 6)" not in text


def test_frontend_uses_latest_assignment_for_ticket_actions() -> None:
    text = APP.read_text(encoding="utf-8")
    inspector_block = text.split("function TicketInspector", 1)[1].split("return (", 1)[0]

    assert "ticket.latestAssignmentId" in inspector_block
    assert "assignment.id === ticket.latestAssignmentId" in inspector_block
    assert "createdAt" in inspector_block


def test_frontend_exposes_daemon_and_execution_evidence_contract() -> None:
    api_types = API_TYPES.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8")
    data = DATA.read_text(encoding="utf-8")
    control = AGENT_CONTROL.read_text(encoding="utf-8")

    assert "export type ApiDaemonStatus" in api_types
    assert "export type ApiTicketEvidenceBundle" in api_types
    assert "daemon_status: ApiDaemonStatus" in api_types
    assert "TicketExecutionEvidence" in app
    assert "ExecutionEvidencePanel" in app
    assert "data.daemonStatus" in app
    assert "本地运行时会自动 claim" in control
    assert "adaptTicketEvidence" in data
    assert "daemonStatus:" in data
    assert "assignmentEventsNeedWorkbenchRefresh" in control
    assert 'event.source === "artifact"' in control
    assert "void onRefresh(ticket.key)" in control


def test_frontend_uses_runtime_level_external_execution_authorization() -> None:
    api_types = API_TYPES.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8")
    control = AGENT_CONTROL.read_text(encoding="utf-8")

    daemon_start_block = api_types.split("export type DaemonStartRequest", 1)[1].split("};", 1)[0]
    run_block = api_types.split("export type RunAssignmentRequest", 1)[1].split("};", 1)[0]

    assert "external_execution_authorized" in daemon_start_block
    assert "external_execution_authorized" not in run_block
    assert "confirm_execution" not in run_block
    assert "授权 Codex/Claude" in app
    assert "external_execution_authorized: true" in control
    assert "target_project_id:" in control
    assert "allowed_backends:" in control
    assert 'scope_mode: "current_assignment"' in control


def test_frontend_inbox_exposes_repair_rerun_acknowledge_resolve_actions() -> None:
    api_client = (ROOT / "frontend" / "ariadne-workbench" / "src" / "shared" / "api" / "client.ts").read_text(
        encoding="utf-8"
    )
    api_types = API_TYPES.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8")

    for endpoint in [
        "/api/inbox/${encodeURIComponent(itemId)}/repair",
        "/api/inbox/${encodeURIComponent(itemId)}/rerun",
        "/api/inbox/${encodeURIComponent(itemId)}/acknowledge",
        "/api/inbox/${encodeURIComponent(itemId)}/resolve",
    ]:
        assert endpoint in api_client
    assert "export type InboxActionRequest" in api_types
    assert "export type InboxActionResponse" in api_types
    for label in ["创建修复任务", "重跑", "确认已读", "标记已解决"]:
        assert label in app
    assert "createInboxRepairTicket(item.id)" in app
    assert "rerunInboxAssignment(item.id)" in app
    assert "acknowledgeInboxItem(item.id)" in app
    assert "resolveInboxItem(item.id)" in app


def test_frontend_product_mode_does_not_silently_fallback_to_fixture() -> None:
    text = DATA.read_text(encoding="utf-8")
    disconnected_block = text.split("if (!offlineFallbackEnabled())", 1)[1].split("try {", 1)[0]

    assert 'source: "disconnected"' in disconnected_block
    assert 'source: "fixture"' not in disconnected_block
    assert "offlineFallbackEnabled" in text


def test_frontend_product_path_is_four_step_compiler_flow() -> None:
    text = APP.read_text(encoding="utf-8")
    page_key_block = text.split("type PageKey", 1)[1].split(";", 1)[0]

    for page in ['"delivery"', '"project"', '"sources"', '"tasks"', '"ready"']:
        assert page in page_key_block
    assert '"knowledge"' not in page_key_block
    assert '"agents"' not in page_key_block
    assert 'initialRoute.page ?? "delivery"' in text
    assert "ProjectVersionDelivery" in (ROOT / "frontend" / "ariadne-workbench" / "src" / "types.ts").read_text(
        encoding="utf-8"
    )
    assert "currentVersionDelivery" in text


def test_frontend_api_contract_exposes_source_analysis_artifacts_and_evidence() -> None:
    text = API_TYPES.read_text(encoding="utf-8")

    assert "export type ApiSourceArtifact" in text
    assert "export type ApiSourceEvidence" in text
    assert "source_artifacts: ApiSourceArtifact[]" in text
    assert "source_evidence: ApiSourceEvidence[]" in text
    for field in ["analysis_status", "artifact_ids", "source_role", "license_risk"]:
        assert field in text


def test_frontend_api_contract_exposes_assignment_readiness() -> None:
    text = API_TYPES.read_text(encoding="utf-8")
    assignment_block = text.split("export type ApiAssignmentSummary", 1)[1].split("};", 1)[0]

    for field in [
        "readiness_status",
        "claimable",
        "route_decision_id",
        "handoff_packet_id",
        "handoff_hash",
        "build_context_id",
    ]:
        assert field in assignment_block


def test_frontend_adapter_consumes_typed_source_outputs() -> None:
    text = DATA.read_text(encoding="utf-8")

    assert "apiData.source_artifacts.map" in text
    assert "apiData.source_evidence.map" in text
    assert "analysisStatus: source.analysis_status" in text
    assert "artifactIds: source.artifact_ids" in text


def test_sources_page_does_not_label_unfetched_github_as_analyzed() -> None:
    app = APP.read_text(encoding="utf-8")
    model = (ROOT / "frontend" / "ariadne-workbench" / "src" / "features" / "project-inputs" / "model.ts").read_text(
        encoding="utf-8"
    )

    assert "已添加，尚未抓取仓库" in app
    assert "处理过程" in app
    assert "source.fetch." in app
    assert "抓取中" in model
    assert "已阻塞" in model


def test_frontend_release_evidence_exposes_guided_readiness_summary() -> None:
    app = APP.read_text(encoding="utf-8")
    types = (ROOT / "frontend" / "ariadne-workbench" / "src" / "types.ts").read_text(
        encoding="utf-8"
    )
    sync_script = (ROOT / "frontend" / "ariadne-workbench" / "scripts" / "sync-local-data.mjs").read_text(
        encoding="utf-8"
    )

    for field in [
        "readinessNextActions",
        "readinessBlockers",
        "evidencePacketStale",
        "evidencePacketStaleReasons",
    ]:
        assert field in types
        assert field in sync_script
    assert "下一步" in app
    assert "证据包需要重新生成" in app
    assert "证据过期" in app
