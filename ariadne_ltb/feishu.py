from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ariadne_ltb.models import FailureReason, FeishuWritePlan, FeishuWriteResult, stable_id


def feishu_write_enabled() -> bool:
    return os.environ.get("FEISHU_ENABLE_WRITE") == "1" or os.environ.get(
        "ARIADNE_ENABLE_FEISHU_WRITE"
    ) == "1"


def create_lark_doc_from_plan(
    plan: FeishuWritePlan,
    workspace: Path,
    confirm_write: bool,
    *,
    ticket_key: str = "unknown",
) -> FeishuWriteResult:
    """Create a Feishu/Lark doc through lark-cli when explicitly enabled."""

    workspace.mkdir(parents=True, exist_ok=True)
    result_id = stable_id("feishu_write", plan.id, ticket_key, workspace, _result_nonce())
    if not confirm_write:
        return _blocked_result(
            result_id=result_id,
            plan=plan,
            ticket_key=ticket_key,
            reason="real Feishu writes require --confirm-write",
        )
    if not feishu_write_enabled():
        return _blocked_result(
            result_id=result_id,
            plan=plan,
            ticket_key=ticket_key,
            reason="FEISHU_ENABLE_WRITE=1 or ARIADNE_ENABLE_FEISHU_WRITE=1 is required",
        )

    lark_cli_path = shutil.which("lark-cli")
    if lark_cli_path is None:
        return _blocked_result(
            result_id=result_id,
            plan=plan,
            ticket_key=ticket_key,
            reason="lark-cli is not installed",
            failure_reason=FailureReason.COMMAND_UNAVAILABLE,
        )

    content_path = workspace / f"{plan.id}_feishu_doc.md"
    content_path.write_text(_plan_markdown(plan), encoding="utf-8")
    command = _lark_create_doc_command(lark_cli_path, content_path)
    command_text = _redact_text(shlex.join(command))

    completed = subprocess.run(command, cwd=workspace, text=True, capture_output=True, check=False)
    stdout = _redact_text(completed.stdout)
    stderr = _redact_text(completed.stderr)
    payload = _parse_stdout(stdout)
    document_id = _find_first(payload, ["document_id", "doc_id", "obj_token", "token"])
    document_url = _find_first(payload, ["url", "document_url", "doc_url"])
    ok = completed.returncode == 0
    failure_reason = None if ok else _classify_failure(stdout, stderr)
    reason = None if ok else (stderr or stdout or f"lark-cli exited {completed.returncode}")
    return FeishuWriteResult(
        id=result_id,
        ticket_id=plan.ticket_id,
        ticket_key=ticket_key,
        plan_id=plan.id,
        ok=ok,
        blocked=False,
        dry_run=False,
        failure_reason=failure_reason,
        reason=reason,
        lark_cli_path=lark_cli_path,
        command=command_text,
        returncode=completed.returncode,
        stdout=stdout,
        stderr=stderr,
        content_path=str(content_path),
        document_id=document_id,
        document_url=document_url,
        operation_summary=(
            f"Created Feishu document for {ticket_key}."
            if ok
            else f"Failed to create Feishu document for {ticket_key}."
        ),
    )


def _lark_create_doc_command(lark_cli_path: str, content_path: Path) -> list[str]:
    command = [
        lark_cli_path,
        "docs",
        "+create",
        "--api-version",
        "v2",
        "--doc-format",
        "markdown",
        "--content",
        f"@{content_path.name}",
        "--json",
    ]
    if os.environ.get("FEISHU_FOLDER_TOKEN"):
        command.extend(["--parent-token", os.environ["FEISHU_FOLDER_TOKEN"]])
    return command


def _blocked_result(
    *,
    result_id: str,
    plan: FeishuWritePlan,
    ticket_key: str,
    reason: str,
    failure_reason: FailureReason = FailureReason.EXTERNAL_EXECUTION_BLOCKED,
) -> FeishuWriteResult:
    return FeishuWriteResult(
        id=result_id,
        ticket_id=plan.ticket_id,
        ticket_key=ticket_key,
        plan_id=plan.id,
        ok=False,
        blocked=True,
        dry_run=True,
        failure_reason=failure_reason,
        reason=_redact_text(reason),
        operation_summary=f"Blocked Feishu write for {ticket_key}: {_redact_text(reason)}",
    )


def _parse_stdout(stdout: str) -> dict[str, Any]:
    if not stdout.strip():
        return {}
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return {"stdout": stdout}
    return payload if isinstance(payload, dict) else {"stdout": payload}


def _find_first(payload: Any, keys: list[str]) -> str | None:
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
        for value in payload.values():
            found = _find_first(value, keys)
            if found:
                return found
    if isinstance(payload, list):
        for item in payload:
            found = _find_first(item, keys)
            if found:
                return found
    return None


def _classify_failure(stdout: str, stderr: str) -> FailureReason:
    text = f"{stdout}\n{stderr}".lower()
    if any(marker in text for marker in ["login", "auth", "unauthorized", "permission denied"]):
        return FailureReason.AUTHENTICATION_FAILED
    if any(marker in text for marker in ["rate limit", "quota", "too many requests"]):
        return FailureReason.QUOTA_EXCEEDED
    return FailureReason.AGENT_ERROR


def _redact_text(text: str) -> str:
    redacted = text
    for secret in _secret_values():
        redacted = redacted.replace(secret, "[REDACTED]")
    redacted = re.sub(
        r"(?i)(token|secret|key|authorization|password)=([^\\s'\";]+)",
        r"\1=[REDACTED]",
        redacted,
    )
    redacted = re.sub(r"(?i)(bearer\\s+)[A-Za-z0-9._~+/=-]+", r"\1[REDACTED]", redacted)
    return redacted


def _secret_values() -> list[str]:
    values: list[str] = []
    for name, value in os.environ.items():
        upper = name.upper()
        if not value or len(value) < 4:
            continue
        if any(marker in upper for marker in ["SECRET", "TOKEN", "API_KEY", "PASSWORD"]):
            values.append(value)
    return sorted(set(values), key=len, reverse=True)


def _plan_markdown(plan: FeishuWritePlan) -> str:
    doc = plan.proposed_docs[0] if plan.proposed_docs else {"title": "Ariadne Write-back"}
    title = doc.get("title", "Ariadne Write-back")
    body = doc.get("body_markdown", "")
    outline = "\n".join(f"- {item}" for item in doc.get("outline", []))
    tasks = "\n".join(f"- {task.get('title', 'Untitled task')}" for task in plan.proposed_tasks)
    actions = "\n".join(f"- {action}" for action in plan.next_actions)
    return f"""# {title}

{body}

## Outline

{outline or '- None'}

## Decision Log

{plan.decision_log_entry}

## Proposed Tasks

{tasks or '- None'}

## Run Summary

{plan.run_summary}

## Next Actions

{actions or '- None'}
"""


def _result_nonce() -> str:
    from ariadne_ltb.models import utc_now

    return utc_now()
