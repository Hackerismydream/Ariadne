from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_TYPES = ROOT / "frontend" / "ariadne-workbench" / "src" / "shared" / "api" / "types.ts"
API_CLIENT = ROOT / "frontend" / "ariadne-workbench" / "src" / "shared" / "api" / "client.ts"
APP = ROOT / "frontend" / "ariadne-workbench" / "src" / "App.tsx"
ROUTES = ROOT / "frontend" / "ariadne-workbench" / "src" / "app" / "routes.ts"
SIDEBAR = ROOT / "frontend" / "ariadne-workbench" / "src" / "app" / "shell" / "Sidebar.tsx"
CURRENT_STRIP = (
    ROOT / "frontend" / "ariadne-workbench" / "src" / "widgets" / "current-version" / "CurrentVersionStrip.tsx"
)
ISSUES_PAGE = ROOT / "frontend" / "ariadne-workbench" / "src" / "pages" / "issues" / "IssuesPage.tsx"
ISSUE_DETAIL = ROOT / "frontend" / "ariadne-workbench" / "src" / "pages" / "issues" / "IssueDetail.tsx"
TEAM_PAGE = ROOT / "frontend" / "ariadne-workbench" / "src" / "pages" / "team" / "TeamPage.tsx"
RUNS_PAGE = ROOT / "frontend" / "ariadne-workbench" / "src" / "pages" / "runs" / "RunsPage.tsx"
INBOX_PAGE = ROOT / "frontend" / "ariadne-workbench" / "src" / "pages" / "inbox" / "InboxPage.tsx"
SOURCES_PAGE = ROOT / "frontend" / "ariadne-workbench" / "src" / "pages" / "sources" / "SourcesPage.tsx"
PLAN_CHANGES_PAGE = ROOT / "frontend" / "ariadne-workbench" / "src" / "pages" / "plan-changes" / "PlanChangesPage.tsx"
BACKLOG_LIB = ROOT / "frontend" / "ariadne-workbench" / "src" / "shared" / "lib" / "backlog.ts"
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
    text = ISSUE_DETAIL.read_text(encoding="utf-8")

    assert "issue.timeline.map((event)" in text
    assert "assignmentEvents.slice(-12)" not in text
    assert "assignmentEvents.slice(0, 6)" not in text


def test_frontend_uses_latest_assignment_for_ticket_actions() -> None:
    text = ISSUE_DETAIL.read_text(encoding="utf-8")
    client = API_CLIENT.read_text(encoding="utf-8")

    assert "assignIssue(issueKey" in text
    assert "runIssueNow(issueKey" in text
    assert "retryAssignment(assignment.id" in text
    assert "assignment.retry_allowed" in text
    assert "/api/assignments/${encodeURIComponent(assignmentId)}/retry" in client
    assert "addIssueComment(issueKey" in text


def test_frontend_exposes_daemon_and_execution_evidence_contract() -> None:
    api_types = API_TYPES.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8")
    issue_detail = ISSUE_DETAIL.read_text(encoding="utf-8")
    data = DATA.read_text(encoding="utf-8")
    control = AGENT_CONTROL.read_text(encoding="utf-8")

    assert "export type ApiDaemonStatus" in api_types
    assert "export type ApiTicketEvidenceBundle" in api_types
    assert "daemon_status: ApiDaemonStatus" in api_types
    assert "ApiIssueExecutionResultSummary" in api_types
    assert "Execution Results" in issue_detail
    assert "Diff / Tests / Review" in issue_detail
    assert "data.daemonStatus" in app
    assert "本地运行时会自动 claim" in control
    assert "adaptTicketEvidence" in data
    assert "daemonStatus:" in data
    assert "assignmentEventsNeedWorkbenchRefresh" in control
    assert 'event.source === "artifact"' in control
    assert "void onRefresh(ticket.key)" in control


def test_frontend_uses_runtime_level_external_execution_authorization() -> None:
    api_types = API_TYPES.read_text(encoding="utf-8")
    control = AGENT_CONTROL.read_text(encoding="utf-8")
    runs_page = RUNS_PAGE.read_text(encoding="utf-8")

    daemon_start_block = api_types.split("export type DaemonStartRequest", 1)[1].split("};", 1)[0]
    run_block = api_types.split("export type RunAssignmentRequest", 1)[1].split("};", 1)[0]

    assert "external_execution_authorized" in daemon_start_block
    assert "external_execution_authorized" not in run_block
    assert "confirm_execution" not in run_block
    assert "Codex/Claude allowed" in runs_page
    assert "startScopedDaemon" in runs_page
    assert "allowed_assignment_id:" in runs_page
    assert 'scope_mode: assignment ? "assignment" : "project"' in runs_page
    assert "external_execution_authorized: true" in control
    assert "target_project_id:" in control
    assert "allowed_backends:" in control
    assert 'scope_mode: "current_assignment"' in control


def test_frontend_inbox_exposes_repair_rerun_acknowledge_resolve_actions() -> None:
    api_client = (ROOT / "frontend" / "ariadne-workbench" / "src" / "shared" / "api" / "client.ts").read_text(
        encoding="utf-8"
    )
    api_types = API_TYPES.read_text(encoding="utf-8")
    inbox_page = INBOX_PAGE.read_text(encoding="utf-8")

    for endpoint in [
        "/api/inbox/${encodeURIComponent(itemId)}/repair",
        "/api/inbox/${encodeURIComponent(itemId)}/rerun",
        "/api/inbox/${encodeURIComponent(itemId)}/acknowledge",
        "/api/inbox/${encodeURIComponent(itemId)}/resolve",
    ]:
        assert endpoint in api_client
    assert "export type InboxActionRequest" in api_types
    assert "export type InboxActionResponse" in api_types
    for label in ["Repair", "Rerun", "Acknowledge", "Resolve"]:
        assert label in inbox_page
    assert "createInboxRepairTicket(item.id)" in inbox_page
    assert "rerunInboxAssignment(item.id" in inbox_page
    assert "acknowledgeInboxItem(item.id" in inbox_page
    assert "resolveInboxItem(item.id" in inbox_page


def test_frontend_product_mode_does_not_silently_fallback_to_fixture() -> None:
    text = DATA.read_text(encoding="utf-8")

    assert 'export type WorkbenchDataSource = "api" | "disconnected"' in text
    assert 'source: "disconnected"' in text
    assert 'source: "fixture"' not in text
    assert 'source: "snapshot"' not in text
    assert "/web_data/workbench.json" not in text
    assert "offlineFallbackEnabled" not in text
    assert "ARI-FE-001" not in text


def test_frontend_product_path_defaults_to_current_issues_context() -> None:
    text = APP.read_text(encoding="utf-8")
    routes = ROUTES.read_text(encoding="utf-8")
    sidebar = SIDEBAR.read_text(encoding="utf-8")
    current_strip = CURRENT_STRIP.read_text(encoding="utf-8")
    page_key_block = routes.split("export type PageKey", 1)[1].split(";", 1)[0]

    for page in ['"delivery"', '"project"', '"sources"', '"tasks"', '"ready"', '"team"', '"runs"', '"inbox"']:
        assert page in page_key_block
    assert '"knowledge"' not in page_key_block
    assert '"agents"' not in page_key_block
    assert 'team: "team"' in routes
    assert 'runs: "runs"' in routes
    assert 'inbox: "inbox"' in routes
    assert 'key: "team"' in sidebar
    assert 'key: "runs"' in sidebar
    assert 'key: "inbox"' in sidebar
    assert 'redirectHash: "#issues"' in routes
    assert 'initialRoute.page ?? "ready"' in text
    assert "CurrentVersionStrip" in text
    assert "Current Version Context" in current_strip
    assert "ProjectVersionDelivery" in (ROOT / "frontend" / "ariadne-workbench" / "src" / "types.ts").read_text(
        encoding="utf-8"
    )
    assert "currentVersionDelivery" in text
    for label in ["Issues", "Sources", "Plan Changes", "Team", "Runs", "Inbox", "Diagnostics"]:
        assert label in sidebar


def test_frontend_exposes_knowledge_to_issue_provenance_contract() -> None:
    api_types = API_TYPES.read_text(encoding="utf-8")
    data = DATA.read_text(encoding="utf-8")
    sources_page = SOURCES_PAGE.read_text(encoding="utf-8")
    plan_page = PLAN_CHANGES_PAGE.read_text(encoding="utf-8")

    for field in [
        "compiler_provenance",
        "codebase_snapshot_status",
        "source_claim_trace",
        "affected_module_rationale",
        "acceptance_criteria_rationale",
        "quality_status",
        "origin_bucket",
        "claim_count",
    ]:
        assert field in api_types
    for adapter_field in [
        "compilerProvenance",
        "codebaseSnapshotStatus",
        "sourceClaimTrace",
        "affectedModuleRationale",
        "acceptanceCriteriaRationale",
        "qualityStatus",
        "originBucket",
        "claimCount",
    ]:
        assert adapter_field in data
    for label in ["Compiler provenance", "Target codebase snapshot", "Source claim trace"]:
        assert label in plan_page
    for label in ["External inputs", "Target codebase", "Internal derived sources"]:
        assert label in sources_page


def test_frontend_phase4_pages_consume_page_scoped_api_contracts() -> None:
    api_client = (ROOT / "frontend" / "ariadne-workbench" / "src" / "shared" / "api" / "client.ts").read_text(
        encoding="utf-8"
    )
    app = APP.read_text(encoding="utf-8")
    routes = ROUTES.read_text(encoding="utf-8")
    team_page = TEAM_PAGE.read_text(encoding="utf-8")
    runs_page = RUNS_PAGE.read_text(encoding="utf-8")
    inbox_page = INBOX_PAGE.read_text(encoding="utf-8")

    for helper in [
        "getTeamAgents",
        "getTeamBuildTeams",
        "getTeamSkills",
        "getRunsRuntimes",
        "getRunsAssignments",
        "getInbox",
    ]:
        assert f"export function {helper}" in api_client

    assert "TeamPage" in app
    assert "RunsPage" in app
    assert "InboxControlPage" in app
    assert 'page === "team"' in app
    assert 'page === "runs"' in app
    assert 'page === "inbox"' in app
    assert 'team: "diagnostics"' not in routes
    assert 'runs: "diagnostics"' not in routes
    assert 'inbox: "diagnostics"' not in routes
    for helper in ["getTeamAgents", "getTeamBuildTeams", "getTeamSkills"]:
        assert helper in team_page
    for helper in ["getRunsRuntimes", "getRunsAssignments", "getDaemonStatus", "startDaemon", "stopDaemon"]:
        assert helper in runs_page
    assert "disabled_reasons" in runs_page
    for helper in [
        "getInbox",
        "createInboxRepairTicket",
        "rerunInboxAssignment",
        "acknowledgeInboxItem",
        "resolveInboxItem",
    ]:
        assert helper in inbox_page


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
    sources_page = SOURCES_PAGE.read_text(encoding="utf-8")
    model = (ROOT / "frontend" / "ariadne-workbench" / "src" / "features" / "project-inputs" / "model.ts").read_text(
        encoding="utf-8"
    )

    assert "Paste a URL, GitHub repo, or local path" in sources_page
    assert "Source lifecycle" in sources_page
    assert "Typed artifacts" in sources_page
    assert "Evidence snippets" in sources_page
    assert "Go to Plan Changes" in sources_page
    assert "抓取中" in model
    assert "已阻塞" in model


def test_frontend_phase5_sources_and_plan_changes_are_extracted() -> None:
    app = APP.read_text(encoding="utf-8")
    client = (ROOT / "frontend" / "ariadne-workbench" / "src" / "shared" / "api" / "client.ts").read_text(
        encoding="utf-8"
    )
    sources_page = SOURCES_PAGE.read_text(encoding="utf-8")
    plan_page = PLAN_CHANGES_PAGE.read_text(encoding="utf-8")
    backlog_lib = BACKLOG_LIB.read_text(encoding="utf-8")

    assert "SourcesPage" in app
    assert "PlanChangesPage" in app
    assert "function KnowledgePage" not in app
    assert "function TasksPage" not in app
    assert "function groupBacklogChanges" not in app
    assert "export function groupBacklogChanges" in backlog_lib
    assert "getSourceDetail" in client
    assert "refreshIssueFactoryPreview" in client
    for text in ["Paste a URL, GitHub repo, or local path", "Add and Analyze", "Source lifecycle"]:
        assert text in sources_page
    for text in ["Issue Delta", "Generate Issue Delta", "Apply Changes", "View Issues", "Refresh Preview"]:
        assert text in plan_page
    assert "stale_preview" in plan_page


def test_frontend_release_evidence_exposes_guided_readiness_summary() -> None:
    issue_detail = ISSUE_DETAIL.read_text(encoding="utf-8")
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
    assert "Diff / Tests / Review" in issue_detail
    assert "Execution Results" in issue_detail
    assert "next_issue_links" in issue_detail
