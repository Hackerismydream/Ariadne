from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ariadne_ltb.storage import AriadneStore


REAL_CLOSED = "REAL_CLOSED"
BLOCKED_WITH_EVIDENCE = "BLOCKED_WITH_EVIDENCE"
OFFLINE_REGRESSION = "OFFLINE_REGRESSION"
NOT_CLOSED = "NOT_CLOSED"

PRODUCT_CLOSURE_COMMAND = "ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 scripts/verify_dogfood_browser.sh --real"
PRODUCT_CLOSURE_PATH = "browser_project_version_delivery"
REAL_BACKENDS = {"codex", "claude", "claude-code"}
OFFLINE_BACKENDS = {"fake-codex", "dry-run"}
OFFLINE_MARKER = "fix" + "ture"
FORBIDDEN_REAL_CLOSURE_MARKERS = (
    "fake-codex",
    "demo full",
    "dry-run",
    "static " + OFFLINE_MARKER,
    "blocked rehearsal",
    "演练模式",
    "门禁关闭",
    "已阻塞",
)
FORBIDDEN_REAL_CLOSURE_PATTERNS = (
    "dry_run:true",
    '"dry_run":true',
    "blocked:true",
    '"blocked":true',
)


def product_closure_snapshot(store: AriadneStore, project_version_id: str | None = None) -> dict[str, Any]:
    """Classify Project Version Delivery closure without mutating product state."""
    packet = _latest_dogfood_packet(store, project_version_id=project_version_id)
    blocker = _latest_blocker_packet(store, project_version_id=project_version_id)
    if packet and (not blocker or packet.stat().st_mtime >= blocker.stat().st_mtime):
        return _with_defaults(
            evaluate_closure_packet(
                _read_json(packet),
                packet_path=packet,
                validate_target_path=True,
            )
        )
    if blocker:
        return _with_defaults(_blocked_snapshot(blocker))

    offline = _latest_offline_evidence(store)
    if offline:
        return _with_defaults(
            {
                "status": OFFLINE_REGRESSION,
                "mode": "offline_regression",
                "summary": "Offline regression evidence exists, but it is not product closure.",
                "reason": offline,
                "packet_path": None,
            }
        )

    blocked = _latest_blocked_real_evidence(store)
    if blocked:
        return _with_defaults(
            {
                "status": BLOCKED_WITH_EVIDENCE,
                "mode": "blocked_diagnostic",
                "summary": "A real Codex/Claude attempt is blocked with evidence.",
                "reason": blocked,
                "packet_path": None,
            }
        )

    cli_only = _latest_cli_only_real_success(store)
    if cli_only:
        return _with_defaults(
            {
                "status": NOT_CLOSED,
                "mode": "cli_only_success",
                "summary": "Real backend evidence exists, but browser Project Version Delivery closure was not recorded.",
                "reason": cli_only,
                "packet_path": None,
            }
        )

    return _with_defaults(
        {
            "status": NOT_CLOSED,
            "mode": "not_attempted",
            "summary": "No browser Project Version Delivery closure packet has been recorded.",
            "reason": f"Run `{PRODUCT_CLOSURE_COMMAND}` for product closure.",
            "packet_path": None,
        }
    )


def evaluate_closure_packet(
    packet: dict[str, Any],
    *,
    packet_path: Path | None = None,
    validate_target_path: bool = False,
) -> dict[str, Any]:
    status = str(packet.get("status") or "")
    mode = str(packet.get("mode") or "")
    evidence = str(packet.get("execution_evidence_text") or "")
    found_markers = _forbidden_real_closure_markers(evidence)
    if status in {BLOCKED_WITH_EVIDENCE, "BLOCKED_NOT_CLOSED"} or mode in {"blocked-ok", "blocked"}:
        return {
            "status": BLOCKED_WITH_EVIDENCE,
            "mode": "blocked_diagnostic",
            "summary": "Browser Project Version Delivery produced blocker evidence.",
            "reason": _packet_reason(packet) or "Browser path blocked before REAL_CLOSED.",
            "packet_path": str(packet_path) if packet_path else None,
            "forbidden_markers": found_markers,
        }

    if status == REAL_CLOSED:
        if mode != "real":
            return _packet_rejected(
                OFFLINE_REGRESSION,
                mode or "unknown",
                f"REAL_CLOSED requires mode=real, got mode={mode or 'unknown'}.",
                packet_path,
                found_markers,
            )
        if found_markers:
            return _packet_rejected(
                OFFLINE_REGRESSION,
                "offline_regression",
                f"REAL_CLOSED evidence contains non-product markers: {', '.join(found_markers)}.",
                packet_path,
                found_markers,
            )
        workbench_url = str(packet.get("workbench_url") or "")
        if not workbench_url.startswith(("http://", "https://")):
            return _packet_rejected(
                NOT_CLOSED,
                "missing_browser_path",
                "REAL_CLOSED requires a browser Workbench URL.",
                packet_path,
                found_markers,
            )
        target_error = _target_path_error(packet) if validate_target_path else ""
        if target_error:
            return _packet_rejected(
                NOT_CLOSED,
                "invalid_target_project",
                target_error,
                packet_path,
                found_markers,
            )
        return {
            "status": REAL_CLOSED,
            "mode": PRODUCT_CLOSURE_PATH,
            "summary": "Browser Project Version Delivery reached REAL_CLOSED.",
            "reason": "",
            "packet_path": str(packet_path) if packet_path else None,
            "forbidden_markers": [],
        }

    if mode in {"demo", OFFLINE_MARKER, "offline", "dry-run", "dry_run"} or found_markers:
        return {
            "status": OFFLINE_REGRESSION,
            "mode": "offline_regression",
            "summary": "Offline evidence cannot satisfy product closure.",
            "reason": _packet_reason(packet) or "Closure packet contains offline regression markers.",
            "packet_path": str(packet_path) if packet_path else None,
            "forbidden_markers": found_markers,
        }

    return {
        "status": NOT_CLOSED,
        "mode": "not_closed",
        "summary": "Closure packet is not a REAL_CLOSED browser result.",
        "reason": _packet_reason(packet) or f"dogfood status is not REAL_CLOSED: {status or 'missing'}",
        "packet_path": str(packet_path) if packet_path else None,
        "forbidden_markers": found_markers,
    }


def _forbidden_real_closure_markers(evidence: str) -> list[str]:
    normalized = evidence.lower()
    compact = "".join(normalized.split())
    markers = [marker for marker in FORBIDDEN_REAL_CLOSURE_MARKERS if marker.lower() in normalized]
    markers.extend(pattern for pattern in FORBIDDEN_REAL_CLOSURE_PATTERNS if pattern in compact)
    return markers


def _with_defaults(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": snapshot["status"],
        "mode": snapshot.get("mode") or "unknown",
        "summary": snapshot.get("summary") or "",
        "reason": snapshot.get("reason") or "",
        "packet_path": snapshot.get("packet_path"),
        "required_command": PRODUCT_CLOSURE_COMMAND,
        "acceptance_path": PRODUCT_CLOSURE_PATH,
        "forbidden_markers": snapshot.get("forbidden_markers") or [],
    }


def _packet_rejected(
    status: str,
    mode: str,
    reason: str,
    packet_path: Path | None,
    found_markers: list[str],
) -> dict[str, Any]:
    return {
        "status": status,
        "mode": mode,
        "summary": "Closure packet was rejected by the product closure gate.",
        "reason": reason,
        "packet_path": str(packet_path) if packet_path else None,
        "forbidden_markers": found_markers,
    }


def _latest_dogfood_packet(store: AriadneStore, project_version_id: str | None = None) -> Path | None:
    return _latest_path(
        _paths_matching_project_version(
            store.root.glob(".ariadne/dogfood/**/closure-result.json"),
            project_version_id,
        )
    )


def _latest_blocker_packet(store: AriadneStore, project_version_id: str | None = None) -> Path | None:
    return _latest_path(
        _paths_matching_project_version(
            store.root.glob(".ariadne/dogfood/**/current-blocker.json"),
            project_version_id,
        )
    )


def _paths_matching_project_version(paths: Any, project_version_id: str | None) -> list[Path]:
    present = [path for path in paths if path.exists()]
    if not project_version_id:
        return present
    exact_matches = [
        path
        for path in present
        if _packet_project_version_id(_read_json(path)) == project_version_id
    ]
    if exact_matches:
        return exact_matches
    return [
        path
        for path in present
        if _packet_project_version_id(_read_json(path)) is None
    ]


def _packet_project_version_id(packet: dict[str, Any]) -> str | None:
    project = packet.get("project")
    if isinstance(project, dict) and project.get("project_version_id"):
        return str(project["project_version_id"])
    for key in ("project_version_id", "target_project_version_id"):
        if packet.get(key):
            return str(packet[key])
    return None


def _latest_path(paths: Any) -> Path | None:
    present = [path for path in paths if path.exists()]
    if not present:
        return None
    return sorted(present, key=lambda path: path.stat().st_mtime)[-1]


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": NOT_CLOSED, "reason": f"{path} is not readable JSON"}
    return data if isinstance(data, dict) else {"status": NOT_CLOSED, "reason": f"{path} is not a JSON object"}


def _blocked_snapshot(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    reason = _packet_reason(payload) or payload.get("message") or "Browser path recorded a blocker."
    return {
        "status": BLOCKED_WITH_EVIDENCE,
        "mode": "blocked_diagnostic",
        "summary": "Browser Project Version Delivery is blocked with captured evidence.",
        "reason": str(reason),
        "packet_path": str(path),
    }


def _target_path_error(packet: dict[str, Any]) -> str:
    target_repo = packet.get("target_repo")
    nested_target = target_repo.get("path") if isinstance(target_repo, dict) else ""
    raw_target = str(packet.get("target_path") or nested_target or "")
    if not raw_target:
        return "REAL_CLOSED requires target_path."
    target = Path(raw_target).expanduser()
    if not target.exists():
        return f"target project path does not exist: {target}"
    if not (target / ".git").exists():
        return f"target project is not a git repo: {target}"
    return ""


def _packet_reason(packet: dict[str, Any]) -> str:
    for key in ("reason", "blocker", "message", "error"):
        value = packet.get(key)
        if value:
            return str(value)
    return ""


def _latest_offline_evidence(store: AriadneStore) -> str:
    executions = [
        result
        for result in store.list_execution_results()
        if result.dry_run or result.backend_name in OFFLINE_BACKENDS
    ]
    if executions:
        latest = sorted(executions, key=lambda item: item.ended_at)[-1]
        backend = "dry-run" if latest.dry_run else latest.backend_name
        return f"{backend} execution {latest.id} is offline regression evidence only."
    smoke = [
        result
        for result in store.list_backend_smoke_evidence()
        if result.backend_name in OFFLINE_BACKENDS
    ]
    if smoke:
        latest_smoke = sorted(smoke, key=lambda item: item.created_at)[-1]
        return f"{latest_smoke.backend_name} backend smoke {latest_smoke.id} is offline regression evidence only."
    return ""


def _latest_blocked_real_evidence(store: AriadneStore) -> str:
    blocked_executions = [
        result
        for result in store.list_execution_results()
        if result.backend_name in REAL_BACKENDS and not result.dry_run and result.blocked
    ]
    if blocked_executions:
        latest = sorted(blocked_executions, key=lambda item: item.ended_at)[-1]
        return latest.block_reason or latest.provider_failure_kind or f"{latest.backend_name} execution {latest.id} blocked."
    blocked_smoke = [
        result
        for result in store.list_backend_smoke_evidence()
        if result.backend_name in REAL_BACKENDS and result.blocked
    ]
    if blocked_smoke:
        latest_smoke = sorted(blocked_smoke, key=lambda item: item.created_at)[-1]
        return latest_smoke.blocker or f"{latest_smoke.backend_name} backend smoke {latest_smoke.id} blocked."
    return ""


def _latest_cli_only_real_success(store: AriadneStore) -> str:
    executions = [
        result
        for result in store.list_execution_results()
        if result.backend_name in REAL_BACKENDS
        and not result.dry_run
        and not result.blocked
        and result.exit_code == 0
        and result.test_exit_code in {0, None}
    ]
    smoke = [
        result
        for result in store.list_backend_smoke_evidence()
        if result.backend_name in REAL_BACKENDS
        and result.succeeded
        and result.assignment_status == "done"
        and result.exit_code == 0
        and result.test_exit_code == 0
        and result.review_verdict == "pass"
    ]
    latest_execution = sorted(executions, key=lambda item: item.ended_at)[-1] if executions else None
    latest_smoke = sorted(smoke, key=lambda item: item.created_at)[-1] if smoke else None
    if latest_smoke and (not latest_execution or latest_smoke.created_at >= latest_execution.ended_at):
        return f"{latest_smoke.backend_name} backend smoke {latest_smoke.id} is real evidence, but not browser closure."
    if latest_execution:
        return f"{latest_execution.backend_name} execution {latest_execution.id} is real evidence, but not browser closure."
    return ""
