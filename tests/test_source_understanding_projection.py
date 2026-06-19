from __future__ import annotations

from ariadne_ltb.application.dtos import CreateSourceInput, WorkbenchDTO
from ariadne_ltb.application.source_analysis import SourceAnalysisService
from ariadne_ltb.application.web_sources import WebSourceService
from ariadne_ltb.application.workbench_projection import WorkbenchProjectionService
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
