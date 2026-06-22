from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "ariadne-workbench" / "src" / "App.tsx"
SOURCES_PAGE = ROOT / "frontend" / "ariadne-workbench" / "src" / "pages" / "sources" / "SourcesPage.tsx"
PLAN_CHANGES_PAGE = (
    ROOT / "frontend" / "ariadne-workbench" / "src" / "pages" / "plan-changes" / "PlanChangesPage.tsx"
)


def test_sources_page_uses_project_input_language() -> None:
    text = SOURCES_PAGE.read_text(encoding="utf-8")
    assert "Sources" in text
    assert "Add and Analyze" in text
    assert "Source lifecycle" in text
    assert "Typed artifacts" in text
    assert "Evidence snippets" in text
    assert "Relation to goal" in text
    assert "来源收件箱" not in text
    assert "保存来源" not in text


def test_sources_page_does_not_expose_internal_model_names() -> None:
    text = APP.read_text(encoding="utf-8")
    assert "SourceDocument" not in text
    assert "SourceArtifact" not in text
    assert "SourceEvidence" not in text
    assert "BuildContext" not in text


def test_task_generation_explains_selected_analyzed_inputs() -> None:
    text = PLAN_CHANGES_PAGE.read_text(encoding="utf-8")
    assert "Issue Delta" in text
    assert "ready sources" in text
    assert "Generate Issue Delta" in text
    assert "Apply Changes" in text
