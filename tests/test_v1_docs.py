from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_v1_docs_exist_and_name_real_limitations() -> None:
    paths = [
        ROOT / "docs" / "evaluation" / "v1_0_evaluation.md",
        ROOT / "docs" / "demo" / "ARIADNE_V1_DEMO_SCRIPT.md",
        ROOT / "docs" / "interview" / "PROJECT_NARRATIVE.md",
        ROOT / "docs" / "ops" / "V1_RELEASE_CHECKLIST.md",
    ]
    for path in paths:
        assert path.exists(), path
        text = path.read_text(encoding="utf-8")
        assert "Ariadne v1.0" in text
        assert "local" in text.lower() or "本地" in text

    narrative = (ROOT / "docs" / "interview" / "PROJECT_NARRATIVE.md").read_text(
        encoding="utf-8"
    )
    assert "不是普通 RAG" in narrative
    assert "不是重新造 Codex" in narrative
    assert "Multica" in narrative


def test_readme_has_v1_quickstart_and_limitations() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Ariadne v1.0" in readme
    assert "ari daemon run-once" in readme
    assert "ari board serve" in readme
    assert "JSON/JSONL" in readme
