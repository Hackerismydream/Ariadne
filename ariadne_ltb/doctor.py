from __future__ import annotations

import os
from pathlib import Path

from ariadne_ltb.runtime import collect_runtime_capabilities
from ariadne_ltb.storage import AriadneStore


SECRET_ENV_VARS = [
    "DEEPSEEK_API_KEY",
    "FEISHU_APP_ID",
    "FEISHU_APP_SECRET",
    "FEISHU_TENANT_ACCESS_TOKEN",
    "GITHUB_TOKEN",
    "OPENAI_API_KEY",
]


def secret_status_lines() -> list[str]:
    return [f"{name}: {'set' if os.environ.get(name) else 'unset'}" for name in SECRET_ENV_VARS]


def v1_readiness_lines(store: AriadneStore, repo_root: Path) -> list[str]:
    code_root = Path(__file__).resolve().parents[1]
    profiles = store.ensure_default_agent_profiles()
    capabilities = collect_runtime_capabilities()
    fixtures_ok = (code_root / "examples" / "sources").exists()
    board_ok = (store.board_dir / "index.md").exists()
    gitignore_path = repo_root / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path = code_root / ".gitignore"
    gitignore_text = gitignore_path.read_text(encoding="utf-8")
    safety_ok = all(
        pattern in gitignore_text
        for pattern in [".env", ".env.*", "*.secret", "secrets/", ".ariadne/"]
    )
    return [
        f"agent profiles: {'ok' if profiles else 'missing'}",
        f"backend capability: {'ok' if capabilities else 'missing'}",
        f"source fixtures: {'ok' if fixtures_ok else 'missing'}",
        f"ticket count: {len(store.list_tickets())}",
        f"assignment queue: {len(store.list_assignments())}",
        f"journal exists: {'ok' if store.journal_path.exists() else 'missing'}",
        f"board: {'ok' if board_ok else 'missing'}",
        f"safety gates: {'ok' if safety_ok else 'missing'}",
    ]
