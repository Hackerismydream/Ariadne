from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_PATHS = [
    ROOT / "ariadne_ltb",
    ROOT / "frontend" / "ariadne-workbench" / "src",
    ROOT / "scripts",
]
FORBIDDEN_PRODUCT_MARKERS = [
    "mock",
    "fixture",
    "sample data",
    "static fixture",
    "offline fixture",
    "placeholder data",
    "hardcoded data",
    "VITE_ARIADNE_OFFLINE_FIXTURE",
    "/web_data/workbench.json",
]


def test_product_code_does_not_use_mock_or_fixture_data() -> None:
    violations: list[str] = []
    for base in PRODUCT_PATHS:
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".ts", ".tsx", ".js", ".mjs", ".sh"}:
                continue
            text = path.read_text(encoding="utf-8")
            lower = text.lower()
            for marker in FORBIDDEN_PRODUCT_MARKERS:
                if marker.lower() in lower:
                    violations.append(f"{path.relative_to(ROOT)} contains {marker!r}")
    assert not violations, "\n".join(violations)
