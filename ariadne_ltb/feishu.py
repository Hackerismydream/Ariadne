from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from ariadne_ltb.models import FeishuWritePlan


def feishu_write_enabled() -> bool:
    return os.environ.get("FEISHU_ENABLE_WRITE") == "1" or os.environ.get(
        "ARIADNE_ENABLE_FEISHU_WRITE"
    ) == "1"


def create_lark_doc_from_plan(
    plan: FeishuWritePlan,
    workspace: Path,
    confirm_write: bool,
) -> dict:
    """Create a Feishu/Lark doc through lark-cli when explicitly enabled.

    This is intentionally not used by tests or the default demo. It exists so
    real Feishu writes have one narrow, reviewable path through lark-cli.
    """

    if not confirm_write:
        return {
            "ok": False,
            "dry_run": True,
            "reason": "real Feishu writes require --confirm-write",
        }
    if not feishu_write_enabled():
        return {
            "ok": False,
            "dry_run": True,
            "reason": "FEISHU_ENABLE_WRITE=1 or ARIADNE_ENABLE_FEISHU_WRITE=1 is required",
        }
    if shutil.which("lark-cli") is None:
        return {"ok": False, "dry_run": True, "reason": "lark-cli is not installed"}

    workspace.mkdir(parents=True, exist_ok=True)
    content_path = workspace / f"{plan.id}_feishu_doc.md"
    content_path.write_text(_plan_markdown(plan), encoding="utf-8")
    command = [
        "lark-cli",
        "docs",
        "+create",
        "--api-version",
        "v2",
        "--doc-format",
        "markdown",
        "--content",
        f"@{content_path}",
        "--json",
    ]
    if os.environ.get("FEISHU_FOLDER_TOKEN"):
        command.extend(["--parent-token", os.environ["FEISHU_FOLDER_TOKEN"]])
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    try:
        payload = json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        payload = {"stdout": result.stdout}
    return {
        "ok": result.returncode == 0,
        "dry_run": False,
        "returncode": result.returncode,
        "stdout": payload,
        "stderr": result.stderr,
        "content_path": str(content_path),
    }


def _plan_markdown(plan: FeishuWritePlan) -> str:
    doc = plan.proposed_docs[0] if plan.proposed_docs else {"title": "Ariadne Write-back"}
    title = doc.get("title", "Ariadne Write-back")
    body = doc.get("body_markdown", "")
    tasks = "\n".join(f"- {task.get('title', 'Untitled task')}" for task in plan.proposed_tasks)
    actions = "\n".join(f"- {action}" for action in plan.next_actions)
    return f"""# {title}

{body}

## Decision Log

{plan.decision_log_entry}

## Proposed Tasks

{tasks or '- None'}

## Run Summary

{plan.run_summary}

## Next Actions

{actions or '- None'}
"""
