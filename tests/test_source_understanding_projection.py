from __future__ import annotations

from ariadne_ltb.application.dtos import CreateSourceInput, WorkbenchDTO
from ariadne_ltb.application.source_analysis import SourceAnalysisService
from ariadne_ltb.application.web_sources import WebSourceService
from ariadne_ltb.application.workbench_projection import WorkbenchProjectionService, _current_backlog_previews
from ariadne_ltb.models import BacklogOperation, BacklogOperationType, BacklogPreview, BacklogUpdateTrigger
from ariadne_ltb.storage import AriadneStore


def test_workbench_projects_user_facing_source_understanding(tmp_path):
    store = AriadneStore(tmp_path)
    source = WebSourceService(store).create(
        CreateSourceInput(
            title="SWE-agent/mini-swe-agent",
            source_type="github_repo",
            source_role="reference_project",
            path_or_url="https://github.com/SWE-agent/mini-swe-agent/",
            summary="Reference repository for minimal SWE agent architecture.",
            content="The project demonstrates an agent loop, tool calls, trajectory logging, and tests.",
        )
    )
    SourceAnalysisService(store).analyze_source(source.id)

    workbench = WorkbenchProjectionService(store).snapshot()

    assert isinstance(workbench, WorkbenchDTO)
    assert workbench.source_understandings
    understanding = workbench.source_understandings[0]
    assert understanding.source_id == source.id
    assert understanding.display_title == "SWE-agent/mini-swe-agent"
    assert understanding.kind_label == "GitHub 仓库"
    assert understanding.role_label == "参考项目"
    assert understanding.analysis_label == "分析完成"
    assert understanding.what_ariadne_understood
    assert understanding.evidence_items
    assert understanding.generated_outputs
    assert "SourceDocument" not in understanding.model_dump_json()
    assert "SourceArtifact" not in understanding.model_dump_json()
    assert "SourceEvidence" not in understanding.model_dump_json()


def test_current_backlog_previews_sort_by_created_at_not_id(tmp_path):
    store = AriadneStore(tmp_path)
    target_project_id = "target_project_mini_code_agent"
    old_preview = _preview(
        preview_id="backlog_preview_zzzz_old",
        ticket_key="MCA-001",
        target_project_id=target_project_id,
        created_at="2026-06-28T06:00:00Z",
    )
    new_preview = _preview(
        preview_id="backlog_preview_aaaa_new",
        ticket_key="MCA-002",
        target_project_id=target_project_id,
        created_at="2026-06-28T07:00:00Z",
    )

    store.save_backlog_preview(old_preview)
    store.save_backlog_preview(new_preview)

    previews = _current_backlog_previews(store, target_project_id)

    assert [preview.id for preview in previews] == [
        "backlog_preview_zzzz_old",
        "backlog_preview_aaaa_new",
    ]


def _preview(preview_id: str, ticket_key: str, target_project_id: str, created_at: str) -> BacklogPreview:
    return BacklogPreview(
        id=preview_id,
        trigger_type=BacklogUpdateTrigger.MANUAL_GOAL,
        trigger_ref="goal_1",
        idempotency_key=preview_id,
        base_ticket_fingerprint="base",
        rationale="preview",
        created_at=created_at,
        operations=[
            BacklogOperation(
                id=f"{preview_id}_op",
                operation_type=BacklogOperationType.ADD_TICKET,
                reason="reason",
                ticket_key=ticket_key,
                title="Issue",
                metadata={"target_project_id": target_project_id},
            )
        ],
    )
