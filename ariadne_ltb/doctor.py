from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from ariadne_ltb.github_integration import infer_github_repo
from ariadne_ltb.llm import (
    DEFAULT_DEEPSEEK_BASE_URL,
    DEFAULT_DEEPSEEK_FAST_MODEL,
    DEFAULT_DEEPSEEK_MODEL,
    DEFAULT_LLM_TIMEOUT_SECONDS,
    load_local_env,
)
from ariadne_ltb.models import utc_now
from ariadne_ltb.runtime import collect_runtime_capabilities
from ariadne_ltb.secret_safety import secret_status_lines as secret_scan_status_lines
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.store_doctor import check_store_invariants


SECRET_ENV_VARS = [
    "DEEPSEEK_API_KEY",
    "FEISHU_APP_ID",
    "FEISHU_APP_SECRET",
    "FEISHU_TENANT_ACCESS_TOKEN",
    "GITHUB_TOKEN",
    "OPENAI_API_KEY",
]


def secret_status_lines(root: Path | str = ".") -> list[str]:
    lines = [f"{name}: {'set' if os.environ.get(name) else 'unset'}" for name in SECRET_ENV_VARS]
    lines.extend(secret_scan_status_lines(root))
    return lines


def v1_readiness_lines(store: AriadneStore, repo_root: Path) -> list[str]:
    code_root = Path(__file__).resolve().parents[1]
    profiles = store.ensure_default_agent_profiles()
    capabilities = collect_runtime_capabilities()
    store_invariants = check_store_invariants(store)
    fixtures_ok = (code_root / "examples" / "sources").exists()
    board_ok = (store.board_dir / "index.md").exists()
    gitignore_path = repo_root / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path = code_root / ".gitignore"
    gitignore_text = gitignore_path.read_text(encoding="utf-8")
    safety_ok = all(
        pattern in gitignore_text
        for pattern in [".env", ".env.*", "*.secret", ".secrets", "secrets/", ".ariadne/"]
    )
    return [
        f"agent profiles: {'ok' if profiles else 'missing'}",
        f"backend capability: {'ok' if capabilities else 'missing'}",
        f"source fixtures: {'ok' if fixtures_ok else 'missing'}",
        f"ticket count: {len(store.list_tickets())}",
        f"assignment queue: {len(store.list_assignments())}",
        f"journal exists: {'ok' if store.journal_path.exists() else 'missing'}",
        f"board: {'ok' if board_ok else 'missing'}",
        f"store invariants: {'ok' if store_invariants.ok else 'blocked'}",
        f"store invariant errors: {store_invariants.error_count}",
        f"store invariant warnings: {store_invariants.warning_count}",
        f"safety gates: {'ok' if safety_ok else 'missing'}",
        *secret_scan_status_lines(repo_root),
    ]


def integration_doctor_snapshot(store: AriadneStore, repo_root: Path) -> dict[str, Any]:
    load_local_env(repo_root)
    capabilities = collect_runtime_capabilities()
    store.save_runtime_capabilities(capabilities)
    snapshot: dict[str, Any] = {
        "generated_at": utc_now(),
        "llm": _llm_snapshot(),
        "coding_backends": {
            capability.backend_name: {
                "available": capability.available,
                "command": capability.command,
                "command_path": capability.command_path,
                "external_execution_enabled": capability.external_execution_enabled,
                "command_template_set": capability.command_template_set,
                "confirm_execution_required": capability.confirm_execution_required,
                "disabled_reasons": capability.disabled_reasons,
            }
            for capability in capabilities
            if capability.backend_name in {"codex", "claude-code", "fake-codex", "shell"}
        },
        "feishu": _feishu_snapshot(),
        "github": _github_snapshot(repo_root),
        "safety": {
            "ARIADNE_ENABLE_EXTERNAL_EXECUTION": _set_unset("ARIADNE_ENABLE_EXTERNAL_EXECUTION"),
            "FEISHU_ENABLE_WRITE": _set_unset("FEISHU_ENABLE_WRITE"),
            "confirm_execution_required": True,
            "confirm_write_required": True,
        },
    }
    path = store.doctor_dir / "integrations.json"
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return snapshot


def integration_doctor_lines(store: AriadneStore, repo_root: Path) -> list[str]:
    snapshot = integration_doctor_snapshot(store, repo_root)
    lines = [
        "Integration doctor: ok",
        f"report: {store.doctor_dir / 'integrations.json'}",
        f"DeepSeek API key: {snapshot['llm']['deepseek_api_key']}",
        f"DeepSeek base URL: {snapshot['llm']['base_url']}",
        f"DeepSeek default model: {snapshot['llm']['default_model']}",
        f"CodexBackend command: {_found_missing(snapshot['coding_backends']['codex']['command_path'])}",
        f"ClaudeCodeBackend command: {_found_missing(snapshot['coding_backends']['claude-code']['command_path'])}",
        f"External execution enabled: {snapshot['safety']['ARIADNE_ENABLE_EXTERNAL_EXECUTION']}",
        f"Feishu lark-cli command: {_found_missing(snapshot['feishu']['lark_cli_path'])}",
        f"FEISHU_ENABLE_WRITE: {snapshot['safety']['FEISHU_ENABLE_WRITE']}",
        f"GitHub gh command: {_found_missing(snapshot['github']['gh_path'])}",
        f"GITHUB_TOKEN: {snapshot['github']['GITHUB_TOKEN']}",
        f"GitHub repo: {snapshot['github']['repo'] or 'unknown'}",
        f"GitHub auth status: {snapshot['github']['auth_status']}",
        "Secrets: values redacted",
    ]
    return lines


def _llm_snapshot() -> dict[str, Any]:
    base_url = (
        os.environ.get("ARIADNE_LLM_BASE_URL")
        or os.environ.get("DEEPSEEK_BASE_URL")
        or DEFAULT_DEEPSEEK_BASE_URL
    )
    return {
        "provider": os.environ.get("ARIADNE_LLM_PROVIDER") or "deepseek",
        "deepseek_api_key": _set_unset("DEEPSEEK_API_KEY"),
        "base_url": _safe_url_origin(base_url),
        "default_model": os.environ.get("ARIADNE_LLM_MODEL")
        or os.environ.get("DEEPSEEK_MODEL")
        or DEFAULT_DEEPSEEK_MODEL,
        "fast_model": os.environ.get("ARIADNE_LLM_FAST_MODEL") or DEFAULT_DEEPSEEK_FAST_MODEL,
        "timeout_seconds": _llm_timeout(),
    }


def _feishu_snapshot() -> dict[str, Any]:
    return {
        "lark_cli_path": shutil.which("lark-cli"),
        "FEISHU_ENABLE_WRITE": _set_unset("FEISHU_ENABLE_WRITE"),
        "ARIADNE_ENABLE_FEISHU_WRITE": _set_unset("ARIADNE_ENABLE_FEISHU_WRITE"),
        "FEISHU_APP_ID": _set_unset("FEISHU_APP_ID"),
        "FEISHU_APP_SECRET": _set_unset("FEISHU_APP_SECRET"),
        "FEISHU_TENANT_ACCESS_TOKEN": _set_unset("FEISHU_TENANT_ACCESS_TOKEN"),
        "FEISHU_FOLDER_TOKEN": _set_unset("FEISHU_FOLDER_TOKEN"),
        "confirm_write_required": True,
    }


def _github_snapshot(repo_root: Path) -> dict[str, Any]:
    gh_path = shutil.which("gh")
    auth_status = "unavailable"
    if gh_path:
        auth_status = _gh_auth_status(repo_root)
    return {
        "gh_path": gh_path,
        "GITHUB_TOKEN": _set_unset("GITHUB_TOKEN"),
        "repo": infer_github_repo(repo_root),
        "auth_status": auth_status,
        "confirm_write_required": True,
    }


def _gh_auth_status(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except (FileNotFoundError, NotADirectoryError, PermissionError, subprocess.TimeoutExpired):
        return "failed"
    return "ok" if result.returncode == 0 else "failed"


def _llm_timeout() -> int:
    raw_value = os.environ.get("ARIADNE_LLM_TIMEOUT_SECONDS")
    if not raw_value:
        return DEFAULT_LLM_TIMEOUT_SECONDS
    try:
        value = int(raw_value)
    except ValueError:
        return DEFAULT_LLM_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_LLM_TIMEOUT_SECONDS


def _set_unset(name: str) -> str:
    return "set" if os.environ.get(name) else "unset"


def _found_missing(path: str | None) -> str:
    return f"found {path}" if path else "missing"


def _safe_url_origin(value: str) -> str:
    parsed = urlsplit(value)
    if not parsed.scheme or not parsed.hostname:
        return "[redacted-url]"
    host = parsed.hostname
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, "", "", ""))
