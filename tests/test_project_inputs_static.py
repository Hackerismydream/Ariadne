from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "ariadne-workbench" / "src" / "App.tsx"


def test_sources_page_uses_project_input_language() -> None:
    text = APP.read_text(encoding="utf-8")
    assert "项目输入" in text
    assert "添加并分析" in text
    assert "Ariadne 理解" in text
    assert "关键证据" in text
    assert "影响的任务" in text
    assert "来源收件箱" not in text
    assert "保存来源" not in text


def test_sources_page_does_not_expose_internal_model_names() -> None:
    text = APP.read_text(encoding="utf-8")
    assert "SourceDocument" not in text
    assert "SourceArtifact" not in text
    assert "SourceEvidence" not in text
    assert "BuildContext" not in text


def test_task_generation_explains_selected_analyzed_inputs() -> None:
    text = APP.read_text(encoding="utf-8")
    assert "将使用已分析输入生成任务" in text
    assert "跳过未分析输入" in text
    assert "查看任务建议" in text
