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
    redact_secrets,
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
    real_evidence = _real_evidence_snapshot(store)
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
        _product_evidence_check(
            "real_llm_agent_evidence",
            real_evidence["llm_agents"],
            "DeepSeek-backed Build Lead, Knowledge, Memory, planner, reviewer, and backlog agents have successful evidence.",
            (
                "Run `ari llm run-agent build_lead --ticket <ticket> --confirm-external`, "
                "`ari llm run-agent knowledge --ticket <ticket> --confirm-external`, "
                "`ari llm run-agent memory --ticket <ticket> --confirm-external`, "
                "`ari ticket plan --planner llm`, `ari review run --reviewer llm`, "
                "and `ari ticket run --backlog-planner llm`, then regenerate release evidence."
            ),
        ),
        _product_evidence_check(
            "real_codex_execution_evidence",
            real_evidence["codex"],
            "A real CodexBackend execution succeeded with tests.",
            "Run a confirmed Codex ticket execution and regenerate release evidence.",
        ),
        _product_evidence_check(
            "real_claude_execution_evidence",
            real_evidence["claude_code"],
            "A real ClaudeCodeBackend execution succeeded with tests.",
            "Run a confirmed Claude Code ticket execution and regenerate release evidence.",
        ),
        _product_evidence_check(
            "real_feishu_write_evidence",
            real_evidence["feishu"],
            "A real Feishu write succeeded and produced a document reference.",
            "Run `FEISHU_ENABLE_WRITE=1 ari feishu write <ticket> --confirm-write`.",
        ),
        _product_evidence_check(
            "real_github_write_evidence",
            real_evidence["github"],
            "Real GitHub issue, PR, comment, and status evidence succeeded.",
            (
                "Run `ari github create-issue`, `ari github create-pr`, "
                "`ari github sync`, and `ari github status` for a linked ticket."
            ),
        ),
        _product_github_operation_check(
            "real_github_issue_evidence",
            real_evidence["github"],
            "create_issue",
            "A real GitHub issue was created from an Ariadne ticket.",
            "Run `ari github create-issue <ticket> --confirm-write`.",
        ),
        _product_github_operation_check(
            "real_github_pr_evidence",
            real_evidence["github"],
            "create_pr",
            "A real GitHub PR was created from an Ariadne ticket.",
            "Run `ari github create-pr <ticket> --confirm-write`.",
        ),
        _product_github_operation_check(
            "real_github_comment_evidence",
            real_evidence["github"],
            "sync",
            "A real GitHub issue comment sync was posted.",
            "Run `ari github sync <ticket> --confirm-write`.",
        ),
        _product_github_operation_check(
            "real_github_status_evidence",
            real_evidence["github"],
            "status",
            "A real GitHub issue/PR/status snapshot was captured.",
            "Run `ari github status <ticket>`.",
        ),
    ]
    blocking = [check for check in checks if check["status"] == "blocked"]
    action_required = [check for check in checks if check["status"] == "action_required"]
    gate_check_names = {"external_execution_gate", "feishu_write_gate"}
    acceptance_checks = [check for check in checks if check["name"] not in gate_check_names]
    acceptance_blocking = [check for check in acceptance_checks if check["status"] == "blocked"]
    acceptance_action_required = [
        check for check in acceptance_checks if check["status"] == "action_required"
    ]
    snapshot = {
        "generated_at": utc_now(),
        "overall_status": "blocked" if blocking else "action_required" if action_required else "ready",
        "production_acceptance_status": (
            "blocked"
            if acceptance_blocking
            else "action_required"
            if acceptance_action_required
            else "ready"
        ),
        "run_gate_status": _run_gate_status(checks),
        "checks": checks,
        "integration_report": str(store.doctor_dir / "integrations.json"),
        "release_evidence_packet": release_packet,
        "real_success_evidence": {
            "llm_agents": real_evidence["llm_agents"]["success"],
            "codex": real_evidence["codex"]["success"],
            "claude_code": real_evidence["claude_code"]["success"],
            "feishu": real_evidence["feishu"]["success"],
            "github": real_evidence["github"]["success"],
        },
        "real_failure_evidence": {
            "llm_agents": real_evidence["llm_agents"]["latest_failure"],
            "codex": real_evidence["codex"]["latest_failure"],
            "claude_code": real_evidence["claude_code"]["latest_failure"],
            "feishu": real_evidence["feishu"]["latest_failure"],
            "github": real_evidence["github"]["latest_failure"],
        },
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
        f"Production acceptance: {snapshot['production_acceptance_status']}",
        f"Run gates: {snapshot['run_gate_status']}",
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


def _run_gate_status(checks: list[dict[str, Any]]) -> str:
    gate_checks = [
        check for check in checks if check["name"] in {"external_execution_gate", "feishu_write_gate"}
    ]
    if any(check["status"] == "blocked" for check in gate_checks):
        return "blocked"
    if any(check["status"] == "action_required" for check in gate_checks):
        return "action_required"
    return "ready"


def _product_evidence_check(
    name: str,
    evidence: dict[str, Any],
    ready_summary: str,
    next_action: str,
) -> dict[str, Any]:
    if evidence["success"]:
        return {
            "name": name,
            "status": "ready",
            "summary": ready_summary,
            "next_action": "",
        }
    if evidence["latest_failure"]:
        return {
            "name": name,
            "status": "blocked",
            "summary": evidence["latest_failure"].get("reason") or next_action,
            "next_action": next_action,
        }
    return {
        "name": name,
        "status": "action_required",
        "summary": next_action,
        "next_action": next_action,
    }


def _product_github_operation_check(
    name: str,
    evidence: dict[str, Any],
    operation: str,
    ready_summary: str,
    next_action: str,
) -> dict[str, Any]:
    operation_successes = evidence.get("operation_successes") or {}
    if operation_successes.get(operation):
        return {
            "name": name,
            "status": "ready",
            "summary": ready_summary,
            "next_action": "",
        }
    return {
        "name": name,
        "status": "action_required",
        "summary": next_action,
        "next_action": next_action,
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


def _real_evidence_snapshot(store: AriadneStore) -> dict[str, Any]:
    executions = store.list_execution_results()
    backend_smoke = store.list_backend_smoke_evidence()
    feishu_results = store.list_feishu_write_results()
    github_results = store.list_github_integration_results()
    return {
        "llm_agents": _llm_agent_evidence(store),
        "codex": _backend_smoke_or_execution_evidence(backend_smoke, executions, "codex"),
        "claude_code": _backend_smoke_or_execution_evidence(
            backend_smoke,
            executions,
            "claude-code",
        ),
        "feishu": _feishu_evidence(feishu_results),
        "github": _github_evidence(github_results),
    }


def _llm_agent_evidence(store: AriadneStore) -> dict[str, Any]:
    planner = _llm_planner_evidence(store)
    reviewer = _llm_reviewer_evidence(store)
    backlog = _llm_backlog_evidence(store)
    role_evidence = _llm_role_evidence(store)
    successes = {
        "build_lead": role_evidence["successes"].get("build_lead"),
        "knowledge": role_evidence["successes"].get("knowledge"),
        "memory": role_evidence["successes"].get("memory"),
        "planner": planner["success"],
        "reviewer": reviewer["success"],
        "backlog": backlog["success"],
    }
    missing = [name for name, evidence in successes.items() if not evidence]
    latest_failure = _latest_llm_failure(
        [
            planner["latest_failure"],
            reviewer["latest_failure"],
            backlog["latest_failure"],
            role_evidence["latest_failure"],
        ]
    )
    return {
        "success": _llm_agent_summary(successes) if not missing else None,
        "operation_successes": successes,
        "missing_operations": missing,
        "latest_failure": latest_failure,
    }


def _llm_role_evidence(store: AriadneStore) -> dict[str, Any]:
    artifacts = [
        artifact
        for artifact in _list_artifacts(store)
        if artifact.artifact_type.value == "llm_agent_result"
    ]
    successes: dict[str, Any] = {}
    failures = []
    for role in ["build_lead", "knowledge", "memory"]:
        role_artifacts = [
            artifact for artifact in artifacts if artifact.metadata.get("llm_role") == role
        ]
        successful = [
            artifact for artifact in role_artifacts if artifact.metadata.get("succeeded") is True
        ]
        failed = [
            artifact for artifact in role_artifacts if artifact.metadata.get("succeeded") is False
        ]
        successes[role] = _artifact_success_summary(_latest_by_time(successful, "created_at"))
        failures.extend(failed)
    return {
        "successes": successes,
        "latest_failure": _artifact_failure_summary(_latest_by_time(failures, "created_at")),
    }


def _llm_planner_evidence(store: AriadneStore) -> dict[str, Any]:
    packet_successes = [
        packet
        for packet in store.list_build_packets()
        if packet.metadata.get("planner_mode") == "llm"
    ]
    artifact_successes = [
        artifact
        for artifact in _list_artifacts(store)
        if artifact.artifact_type.value == "build_packet"
        and artifact.metadata.get("planner_mode") == "llm"
    ]
    latest_packet = _build_packet_summary(_latest_by_time(packet_successes, "updated_at"))
    latest_artifact = _artifact_success_summary(_latest_by_time(artifact_successes, "created_at"))
    failures = [
        artifact
        for artifact in _list_artifacts(store)
        if artifact.artifact_type.value == "planner_error"
        and (
            artifact.metadata.get("planner_mode") in {"llm", "llm_blocked"}
            or artifact.metadata.get("planner_name") == "llm"
        )
    ]
    return {
        "success": _latest_llm_success([latest_packet, latest_artifact]),
        "latest_failure": _artifact_failure_summary(_latest_by_time(failures, "created_at")),
    }


def _llm_reviewer_evidence(store: AriadneStore) -> dict[str, Any]:
    successes = [
        review
        for review in store.list_review_reports()
        if review.reviewer_mode == "llm"
    ]
    failures = [
        review for review in store.list_review_reports() if review.reviewer_mode == "llm_blocked"
    ]
    return {
        "success": _review_summary(_latest_by_time(successes, "created_at")),
        "latest_failure": _review_failure_summary(_latest_by_time(failures, "created_at")),
    }


def _llm_backlog_evidence(store: AriadneStore) -> dict[str, Any]:
    artifacts = [
        artifact
        for artifact in _list_artifacts(store)
        if artifact.artifact_type.value == "next_tickets"
        and artifact.metadata.get("source") == "llm_backlog_planner"
    ]
    successes = [artifact for artifact in artifacts if artifact.metadata.get("blocked") is False]
    failures = [artifact for artifact in artifacts if artifact.metadata.get("blocked") is True]
    return {
        "success": _artifact_success_summary(_latest_by_time(successes, "created_at")),
        "latest_failure": _artifact_failure_summary(_latest_by_time(failures, "created_at")),
    }


def _list_artifacts(store: AriadneStore) -> list[Any]:
    return [
        store.load_artifact(path.stem)
        for path in sorted(store.artifact_index_dir.glob("*.json"))
    ]


def _llm_agent_summary(operation_successes: dict[str, Any]) -> dict[str, Any]:
    latest = next(
        (
            operation_successes[operation]
            for operation in ("backlog", "reviewer", "planner", "memory", "knowledge", "build_lead")
            if operation_successes.get(operation)
        ),
        {},
    )
    return {
        "operations": {
            operation: bool(summary)
            for operation, summary in sorted(operation_successes.items())
        },
        "latest_id": latest.get("id"),
        "ticket_id": latest.get("ticket_id"),
        "ticket_key": latest.get("ticket_key"),
        "created_at": latest.get("created_at"),
    }


def _build_packet_summary(packet: Any | None) -> dict[str, Any] | None:
    if packet is None:
        return None
    return {
        "id": packet.id,
        "ticket_id": packet.ticket_id,
        "planner_mode": packet.metadata.get("planner_mode"),
        "build_decision": packet.build_decision.value,
        "updated_at": packet.updated_at,
        "created_at": packet.created_at,
    }


def _review_summary(review: Any | None) -> dict[str, Any] | None:
    if review is None:
        return None
    return {
        "id": review.id,
        "ticket_id": review.ticket_id,
        "reviewer_mode": review.reviewer_mode,
        "verdict": review.verdict.value,
        "risk_score": review.risk_score,
        "created_at": review.created_at,
    }


def _review_failure_summary(review: Any | None) -> dict[str, Any] | None:
    if review is None:
        return None
    reason = "LLM reviewer did not complete successfully"
    if review.required_fixes:
        reason = review.required_fixes[-1]
    return {
        "id": review.id,
        "ticket_id": review.ticket_id,
        "reviewer_mode": review.reviewer_mode,
        "reason": _safe_reason(reason),
        "verdict": review.verdict.value,
        "created_at": review.created_at,
    }


def _artifact_success_summary(artifact: Any | None) -> dict[str, Any] | None:
    if artifact is None:
        return None
    return {
        "id": artifact.id,
        "ticket_id": artifact.ticket_id,
        "artifact_type": artifact.artifact_type.value,
        "path": artifact.path,
        "source": artifact.metadata.get("source"),
        "planner": artifact.metadata.get("planner"),
        "created_at": artifact.created_at,
    }


def _artifact_failure_summary(artifact: Any | None) -> dict[str, Any] | None:
    if artifact is None:
        return None
    reason = artifact.summary
    try:
        path = Path(artifact.path)
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            reason = payload.get("reason") or payload.get("error") or reason
    except (OSError, json.JSONDecodeError, TypeError):
        reason = artifact.summary
    return {
        "id": artifact.id,
        "ticket_id": artifact.ticket_id,
        "artifact_type": artifact.artifact_type.value,
        "reason": _safe_reason(str(reason)),
        "path": artifact.path,
        "created_at": artifact.created_at,
    }


def _latest_llm_failure(failures: list[dict[str, Any] | None]) -> dict[str, Any] | None:
    present = [failure for failure in failures if failure]
    if not present:
        return None
    return sorted(present, key=lambda item: item.get("created_at") or "")[-1]


def _latest_llm_success(successes: list[dict[str, Any] | None]) -> dict[str, Any] | None:
    present = [success for success in successes if success]
    if not present:
        return None
    return sorted(present, key=lambda item: item.get("created_at") or "")[-1]


def _execution_evidence(results: list[Any], backend_name: str) -> dict[str, Any]:
    matching = [result for result in results if result.backend_name == backend_name and not result.dry_run]
    successes = [
        result
        for result in matching
        if not result.blocked and result.exit_code == 0 and result.test_exit_code == 0
    ]
    failures = [result for result in matching if result.blocked or result.exit_code != 0 or result.test_exit_code not in {0, None}]
    return {
        "success": _execution_summary(_latest_by_time(successes, "ended_at")),
        "latest_failure": _execution_failure_summary(_latest_by_time(failures, "ended_at")),
    }


def _backend_smoke_or_execution_evidence(
    smoke_results: list[Any],
    execution_results: list[Any],
    backend_name: str,
) -> dict[str, Any]:
    smoke = _backend_smoke_evidence(smoke_results, backend_name)
    execution = _execution_evidence(execution_results, backend_name)
    return {
        "success": smoke["success"] or execution["success"],
        "latest_failure": smoke["latest_failure"] or execution["latest_failure"],
    }


def _backend_smoke_evidence(results: list[Any], backend_name: str) -> dict[str, Any]:
    matching = [result for result in results if result.backend_name == backend_name]
    successes = [
        result
        for result in matching
        if result.succeeded
        and result.assignment_status == "done"
        and result.exit_code == 0
        and result.test_exit_code == 0
        and result.review_verdict == "pass"
    ]
    failures = [result for result in matching if not result.succeeded]
    return {
        "success": _backend_smoke_summary(_latest_by_time(successes, "created_at")),
        "latest_failure": _backend_smoke_failure_summary(_latest_by_time(failures, "created_at")),
    }


def _backend_smoke_summary(result: Any | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "id": result.id,
        "source": "backend_smoke",
        "ticket_id": result.ticket_id,
        "ticket_key": result.ticket_key,
        "backend_name": result.backend_name,
        "assignment_id": result.assignment_id,
        "execution_result_id": result.execution_result_id,
        "exit_code": result.exit_code,
        "test_exit_code": result.test_exit_code,
        "review_verdict": result.review_verdict,
        "changed_files": result.changed_files,
        "handoff_file": result.handoff_file,
        "board_path": result.board_path,
        "memory_path": result.memory_path,
        "feishu_plan_path": result.feishu_plan_path,
        "next_tickets_path": result.next_tickets_path,
        "agent_runtime": result.agent_runtime,
        "backlog_planner_name": result.backlog_planner_name,
        "created_at": result.created_at,
    }


def _backend_smoke_failure_summary(result: Any | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "id": result.id,
        "source": "backend_smoke",
        "ticket_id": result.ticket_id,
        "ticket_key": result.ticket_key,
        "backend_name": result.backend_name,
        "assignment_id": result.assignment_id,
        "assignment_status": result.assignment_status,
        "execution_result_id": result.execution_result_id,
        "reason": _safe_reason(
            result.blocker
            or result.provider_failure_kind
            or result.failure_reason
            or "backend smoke test did not complete successfully"
        ),
        "exit_code": result.exit_code,
        "test_exit_code": result.test_exit_code,
        "review_verdict": result.review_verdict,
        "failure_reason": result.failure_reason,
        "created_at": result.created_at,
    }


def _feishu_evidence(results: list[Any]) -> dict[str, Any]:
    successes = [
        result
        for result in results
        if result.ok and not result.blocked and not result.dry_run and (result.document_url or result.document_id)
    ]
    failures = [result for result in results if not result.ok or result.blocked]
    return {
        "success": _feishu_summary(_latest_by_time(successes, "created_at")),
        "latest_failure": _integration_failure_summary(_latest_by_time(failures, "created_at")),
    }


def _github_evidence(results: list[Any]) -> dict[str, Any]:
    required_operations = ("create_issue", "create_pr", "sync", "status")
    matching = [result for result in results if result.operation in set(required_operations)]
    successes = [
        result
        for result in matching
        if result.ok and not result.blocked and _github_result_satisfies_operation(result)
    ]
    failures = [result for result in matching if not result.ok or result.blocked]
    operation_successes: dict[str, Any] = {}
    for operation in required_operations:
        latest = _latest_by_time(
            [result for result in successes if result.operation == operation],
            "created_at",
        )
        operation_successes[operation] = _github_summary(latest)
    missing_operations = [
        operation for operation, evidence in operation_successes.items() if not evidence
    ]
    aggregate_success = (
        _github_aggregate_summary(operation_successes)
        if not missing_operations
        else None
    )
    return {
        "success": aggregate_success,
        "operation_successes": operation_successes,
        "missing_operations": missing_operations,
        "latest_failure": _integration_failure_summary(_latest_by_time(failures, "created_at")),
    }


def _github_result_satisfies_operation(result: Any) -> bool:
    if result.operation == "create_issue":
        return bool(result.issue_number and result.issue_url and result.repo)
    if result.operation == "create_pr":
        return bool(result.pr_number and result.pr_url and result.branch and result.repo)
    if result.operation == "sync":
        return bool(result.issue_number and result.comment_url and result.repo)
    if result.operation == "status":
        return bool(result.repo and result.branch and (result.issue_url or result.pr_url or result.commit_sha))
    return False


def _latest_by_time(items: list[Any], field_name: str) -> Any | None:
    if not items:
        return None
    return sorted(items, key=lambda item: getattr(item, field_name) or "")[-1]


def _execution_summary(result: Any | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "id": result.id,
        "ticket_id": result.ticket_id,
        "backend_name": result.backend_name,
        "exit_code": result.exit_code,
        "test_exit_code": result.test_exit_code,
        "changed_files": result.changed_files,
        "handoff_file": result.handoff_file,
        "provider_session_id": result.provider_session_id,
        "ended_at": result.ended_at,
    }


def _execution_failure_summary(result: Any | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "id": result.id,
        "ticket_id": result.ticket_id,
        "backend_name": result.backend_name,
        "reason": _safe_reason(
            result.block_reason or result.provider_failure_kind or "execution did not complete successfully"
        ),
        "exit_code": result.exit_code,
        "test_exit_code": result.test_exit_code,
        "failure_reason": result.failure_reason.value if result.failure_reason else None,
        "ended_at": result.ended_at,
    }


def _feishu_summary(result: Any | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "id": result.id,
        "ticket_id": result.ticket_id,
        "ticket_key": result.ticket_key,
        "document_id": result.document_id,
        "document_url": result.document_url,
        "created_at": result.created_at,
    }


def _github_summary(result: Any | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "id": result.id,
        "ticket_id": result.ticket_id,
        "ticket_key": result.ticket_key,
        "operation": result.operation,
        "repo": result.repo,
        "issue_number": result.issue_number,
        "pr_number": result.pr_number,
        "branch": result.branch,
        "commit_sha": result.commit_sha,
        "issue_url": result.issue_url,
        "pr_url": result.pr_url,
        "comment_url": result.comment_url,
        "created_at": result.created_at,
    }


def _github_aggregate_summary(operation_successes: dict[str, Any]) -> dict[str, Any]:
    latest = next(
        (
            operation_successes[operation]
            for operation in ("status", "sync", "create_pr", "create_issue")
            if operation_successes.get(operation)
        ),
        {},
    )
    return {
        "operations": {
            operation: bool(summary)
            for operation, summary in sorted(operation_successes.items())
        },
        "latest_id": latest.get("id"),
        "ticket_id": latest.get("ticket_id"),
        "ticket_key": latest.get("ticket_key"),
        "repo": latest.get("repo"),
        "issue_number": latest.get("issue_number"),
        "pr_number": latest.get("pr_number"),
        "branch": latest.get("branch"),
        "commit_sha": latest.get("commit_sha"),
        "issue_url": latest.get("issue_url"),
        "pr_url": latest.get("pr_url"),
        "comment_url": operation_successes.get("sync", {}).get("comment_url"),
        "created_at": latest.get("created_at"),
    }


def _integration_failure_summary(result: Any | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "id": result.id,
        "ticket_id": result.ticket_id,
        "ticket_key": result.ticket_key,
        "operation": getattr(result, "operation", None),
        "reason": _safe_reason(result.reason or "integration did not complete successfully"),
        "failure_reason": result.failure_reason.value if result.failure_reason else None,
        "created_at": result.created_at,
    }


def _safe_reason(value: str, max_chars: int = 260) -> str:
    redacted = redact_secrets(value)
    lines = [
        line
        for line in redacted.splitlines()
        if "proxy detected" not in line and "requests (including credentials)" not in line
    ]
    compact = " ".join("\n".join(lines).split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3].rstrip() + "..."
