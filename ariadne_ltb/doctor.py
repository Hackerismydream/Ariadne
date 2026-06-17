from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from ariadne_ltb.github_integration import github_transport_snapshot, infer_github_repo
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
        f"GitHub git transport: {snapshot['github']['git_transport']['status']}",
        "Secrets: values redacted",
    ]
    return lines


def product_readiness_snapshot(store: AriadneStore, repo_root: Path) -> dict[str, Any]:
    """Summarize the production acceptance path without performing remote writes."""
    integration = integration_doctor_snapshot(store, repo_root)
    release_packet = _release_packet_snapshot(store)
    checks = [
        _product_check(
            "deepseek_llm",
            integration["llm"]["deepseek_api_key"] == "set",
            "DeepSeek API key is available for LLM planner/reviewer.",
            "Set DEEPSEEK_API_KEY in the environment or ignored local .env.",
        ),
        _product_check(
            "codex_backend",
            bool(integration["coding_backends"]["codex"]["command_path"]),
            "Codex CLI is available.",
            "Install or repair the local codex command.",
        ),
        _product_check(
            "claude_code_backend",
            bool(integration["coding_backends"]["claude-code"]["command_path"]),
            "Claude Code CLI is available.",
            "Install or repair the local claude command.",
        ),
        _product_check(
            "external_execution_gate",
            integration["safety"]["ARIADNE_ENABLE_EXTERNAL_EXECUTION"] == "set",
            "External execution gate is set for a confirmed real coding run.",
            "Set ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 only when running a confirmed Codex/Claude task.",
            action_required_ok=True,
        ),
        _product_check(
            "feishu_write_gate",
            integration["feishu"]["FEISHU_ENABLE_WRITE"] == "set",
            "Feishu write gate is set for a confirmed real write.",
            "Set FEISHU_ENABLE_WRITE=1 only when running `ari feishu write --confirm-write`.",
            action_required_ok=True,
        ),
        _product_check(
            "feishu_lark_cli",
            bool(integration["feishu"]["lark_cli_path"]),
            "lark-cli is available for Feishu integration.",
            "Install or repair lark-cli before real Feishu writes.",
        ),
        _product_check(
            "github_cli_auth",
            bool(integration["github"]["gh_path"]) and integration["github"]["auth_status"] == "ok",
            "GitHub CLI is installed and authenticated.",
            "Run `gh auth login -h github.com` and retry `ari github doctor`.",
        ),
        _product_check(
            "github_git_transport",
            integration["github"]["git_transport"]["status"] == "ok",
            "Local git transport can read the GitHub branch.",
            "Fix git proxy/credential/SSH transport, then retry `ari github doctor`.",
        ),
        _product_check(
            "release_evidence_packet",
            release_packet["exists"],
            "Release evidence packet exists.",
            "Run `ari evidence packet` after the product workflow.",
        ),
        _product_check(
            "integration_evidence_refs",
            release_packet["has_integration_refs"],
            "Release evidence packet references integration doctor, Feishu, and GitHub evidence.",
            "Run `ari evidence packet` with the current release evidence implementation.",
        ),
    ]
    blocking = [check for check in checks if check["status"] == "blocked"]
    action_required = [check for check in checks if check["status"] == "action_required"]
    snapshot = {
        "generated_at": utc_now(),
        "overall_status": "blocked" if blocking else "action_required" if action_required else "ready",
        "checks": checks,
        "integration_report": str(store.doctor_dir / "integrations.json"),
        "release_evidence_packet": release_packet,
        "next_actions": [
            check["next_action"]
            for check in checks
            if check["status"] in {"blocked", "action_required"}
        ],
    }
    path = store.doctor_dir / "product_readiness.json"
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return snapshot


def product_readiness_lines(store: AriadneStore, repo_root: Path) -> list[str]:
    snapshot = product_readiness_snapshot(store, repo_root)
    lines = [
        f"Product readiness: {snapshot['overall_status']}",
        f"report: {store.doctor_dir / 'product_readiness.json'}",
        f"integration report: {snapshot['integration_report']}",
    ]
    for check in snapshot["checks"]:
        lines.append(f"{check['name']}: {check['status']}")
        if check["status"] != "ready":
            lines.append(f"  next: {check['next_action']}")
    lines.append("Secrets: values redacted")
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
        "git_transport": github_transport_snapshot(repo_root),
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


def _product_check(
    name: str,
    passed: bool,
    ready_summary: str,
    next_action: str,
    *,
    action_required_ok: bool = False,
) -> dict[str, Any]:
    return {
        "name": name,
        "status": "ready" if passed else "action_required" if action_required_ok else "blocked",
        "summary": ready_summary if passed else next_action,
        "next_action": "" if passed else next_action,
    }


def _release_packet_snapshot(store: AriadneStore) -> dict[str, Any]:
    path = store.release_evidence_packet_path
    if not path.exists():
        return {
            "exists": False,
            "path": str(path),
            "has_integration_refs": False,
            "evidence_refs": {},
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "exists": True,
            "path": str(path),
            "has_integration_refs": False,
            "evidence_refs": {},
            "error": "release evidence packet is not valid JSON",
        }
    refs = data.get("evidence_refs") if isinstance(data.get("evidence_refs"), dict) else {}
    required_refs = {"integration_doctor", "runtime_capabilities", "feishu_integrations", "github_integrations"}
    return {
        "exists": True,
        "path": str(path),
        "id": data.get("id"),
        "has_integration_refs": required_refs.issubset(set(refs)),
        "evidence_refs": {key: refs.get(key) for key in sorted(required_refs)},
    }
