from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ariadne_ltb.models import (
    BuildTicket,
    FailureReason,
    GitHubIntegrationResult,
    stable_id,
    utc_now,
)
from ariadne_ltb.storage import AriadneStore


def github_doctor_lines(root: Path) -> list[str]:
    gh_path = shutil.which("gh")
    transport = github_transport_snapshot(root)
    lines = [
        f"gh command: {'found ' + gh_path if gh_path else 'missing'}",
        f"GITHUB_TOKEN: {'set' if os.environ.get('GITHUB_TOKEN') else 'unset'}",
    ]
    repo = infer_github_repo(root)
    lines.append(f"repo: {repo or 'unknown'}")
    lines.append(f"git transport branch: {transport['branch'] or 'unknown'}")
    lines.append(f"git transport status: {transport['status']}")
    if transport["http_proxy"]:
        lines.append(f"git http.proxy: {transport['http_proxy']}")
    if transport["https_proxy"]:
        lines.append(f"git https.proxy: {transport['https_proxy']}")
    if transport["evidence"]:
        lines.append(f"git transport evidence: {transport['evidence'][:240]}")
    direct = transport.get("direct_without_proxy")
    if isinstance(direct, dict):
        lines.append(f"git transport without proxy: {direct['status']}")
        if direct.get("evidence"):
            lines.append(f"git transport without proxy evidence: {direct['evidence'][:240]}")
    if transport.get("suggested_fix"):
        lines.append(f"git transport suggested fix: {transport['suggested_fix']}")
    if not gh_path:
        lines.append("gh auth status: unavailable")
        return lines
    result = _run(["gh", "auth", "status"], cwd=root)
    lines.append(f"gh auth status: {'ok' if result.returncode == 0 else 'failed'}")
    if result.returncode != 0:
        evidence = result.stderr or result.stdout
        if evidence:
            lines.append(f"auth evidence: {_redact_text(evidence).splitlines()[0][:240]}")
    return lines


def github_transport_snapshot(root: Path, branch: str | None = None, timeout_seconds: int = 8) -> dict[str, Any]:
    """Probe local git transport without writing to GitHub."""
    remote_url = _git_output(["git", "config", "--get", "remote.origin.url"], root)
    current_branch = branch or _git_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], root)
    http_proxy = _git_output(["git", "config", "--get", "http.proxy"], root)
    https_proxy = _git_output(["git", "config", "--get", "https.proxy"], root)
    proxy_secrets = _url_userinfo_secrets(http_proxy, https_proxy)
    snapshot: dict[str, Any] = {
        "remote_url": _redact_url(remote_url),
        "branch": current_branch,
        "status": "no_remote" if not remote_url else "unknown",
        "ok": False,
        "failure_reason": None,
        "http_proxy": _redact_url(http_proxy),
        "https_proxy": _redact_url(https_proxy),
        "command": None,
        "exit_code": None,
        "evidence": "",
        "direct_without_proxy": None,
        "suggested_fix": None,
    }
    if not remote_url:
        snapshot["failure_reason"] = FailureReason.INVALID_RESOURCE.value
        snapshot["evidence"] = "remote.origin.url is not configured"
        return snapshot

    probe = _probe_git_transport(
        root,
        current_branch,
        timeout_seconds=timeout_seconds,
        proxy_secrets=proxy_secrets,
        bypass_proxy=False,
    )
    snapshot.update(probe)
    if not snapshot["ok"] and (http_proxy or https_proxy):
        direct_probe = _probe_git_transport(
            root,
            current_branch,
            timeout_seconds=timeout_seconds,
            proxy_secrets=proxy_secrets,
            bypass_proxy=True,
        )
        snapshot["direct_without_proxy"] = direct_probe
        if direct_probe["ok"]:
            snapshot["suggested_fix"] = (
                "Configured git proxy failed, but direct GitHub transport works. "
                "Unset or repair git http.proxy/https.proxy for this repository."
            )
    return snapshot


def _probe_git_transport(
    root: Path,
    branch: str | None,
    *,
    timeout_seconds: int,
    proxy_secrets: list[str],
    bypass_proxy: bool,
) -> dict[str, Any]:
    command = ["git"]
    if bypass_proxy:
        command.extend(["-c", "http.proxy=", "-c", "https.proxy="])
    command.extend(["ls-remote", "--heads", "origin"])
    if branch:
        command.append(branch)
    probe: dict[str, Any] = {
        "command": _redact_command(command),
        "status": "unknown",
        "ok": False,
        "failure_reason": None,
        "exit_code": None,
        "evidence": "",
    }
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        result = subprocess.run(
            command,
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        probe["status"] = "timeout"
        probe["failure_reason"] = FailureReason.TIMEOUT.value
        evidence = "\n".join(part for part in [exc.stdout or "", exc.stderr or ""] if isinstance(part, str))
        probe["evidence"] = (
            _first_line(_redact_dynamic_secrets(evidence, proxy_secrets))
            or f"git transport probe timed out after {timeout_seconds}s"
        )
        return probe
    except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
        probe["status"] = "failed"
        probe["failure_reason"] = FailureReason.COMMAND_UNAVAILABLE.value
        probe["evidence"] = _first_line(_redact_text(str(exc)))
        return probe

    probe["exit_code"] = result.returncode
    probe["evidence"] = _first_line(_redact_dynamic_secrets(result.stderr or result.stdout, proxy_secrets))
    if result.returncode == 0:
        probe["status"] = "ok"
        probe["ok"] = True
        probe["failure_reason"] = None
    else:
        probe["status"] = "failed"
        probe["failure_reason"] = _classify_failure(result.stdout, result.stderr).value
    return probe


def link_ticket_to_github(
    store: AriadneStore,
    ticket: BuildTicket,
    *,
    repo: str | None,
    issue: int | None,
    pr: int | None,
    branch: str | None,
) -> GitHubIntegrationResult:
    resolved_repo = repo or infer_github_repo(store.root)
    github_meta = {
        "repo": resolved_repo,
        "issue": issue,
        "pr": pr,
        "branch": branch,
        "linked_at": utc_now(),
    }
    ticket = ticket.model_copy(
        deep=True,
        update={"metadata": ticket.metadata | {"github": github_meta}},
    )
    store.save_ticket(ticket)
    result = GitHubIntegrationResult(
        id=stable_id("github", ticket.id, "link", resolved_repo, issue, pr, branch),
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        operation="link",
        ok=True,
        repo=resolved_repo,
        issue_number=issue,
        pr_number=pr,
        branch=branch,
        remote_url=_git_output(["git", "config", "--get", "remote.origin.url"], store.root),
        commit_sha=_git_output(["git", "rev-parse", "HEAD"], store.root),
    )
    return result


def create_github_issue_for_ticket(
    store: AriadneStore,
    ticket: BuildTicket,
    *,
    repo: str | None,
    branch: str | None,
    confirm_write: bool,
) -> GitHubIntegrationResult:
    resolved_repo = repo or infer_github_repo(store.root)
    resolved_branch = branch or _git_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], store.root)
    result_id = stable_id("github", ticket.id, "create_issue", resolved_repo, utc_now())
    if not confirm_write:
        return _blocked_result(
            result_id=result_id,
            ticket=ticket,
            operation="create_issue",
            reason="GitHub issue creation writes require --confirm-write",
            repo=resolved_repo,
            issue=None,
            pr=None,
            branch=resolved_branch,
        )
    gh_path = shutil.which("gh")
    if gh_path is None:
        return _blocked_result(
            result_id=result_id,
            ticket=ticket,
            operation="create_issue",
            reason="gh command is not installed",
            failure_reason=FailureReason.COMMAND_UNAVAILABLE,
            repo=resolved_repo,
            issue=None,
            pr=None,
            branch=resolved_branch,
        )
    if not resolved_repo:
        return _blocked_result(
            result_id=result_id,
            ticket=ticket,
            operation="create_issue",
            reason="GitHub repo is required before issue creation",
            failure_reason=FailureReason.INVALID_RESOURCE,
            repo=resolved_repo,
            issue=None,
            pr=None,
            branch=resolved_branch,
        )

    body_path = _write_issue_body(store, ticket)
    title = f"[Ariadne] {ticket.key}: {ticket.title}"
    command = [
        gh_path,
        "issue",
        "create",
        "--repo",
        resolved_repo,
        "--title",
        title,
        "--body-file",
        str(body_path),
    ]
    issue_result = _run(command, cwd=store.root)
    commands = [_redact_command(command)]
    if issue_result.returncode != 0:
        return _failed_result(
            result_id,
            ticket,
            "create_issue",
            resolved_repo,
            None,
            None,
            resolved_branch,
            commands,
            issue_result,
            store.root,
        )

    stdout = _redact_text(issue_result.stdout)
    stderr = _redact_text(issue_result.stderr)
    issue_url = _extract_issue_url(stdout)
    issue_number = _extract_issue_number(issue_url)
    ticket = ticket.model_copy(
        deep=True,
        update={
            "metadata": ticket.metadata
            | {
                "github": {
                    "repo": resolved_repo,
                    "issue": issue_number,
                    "pr": None,
                    "branch": resolved_branch,
                    "linked_at": utc_now(),
                    "created_by": "ariadne",
                }
            }
        },
    )
    store.save_ticket(ticket)
    return GitHubIntegrationResult(
        id=result_id,
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        operation="create_issue",
        ok=True,
        blocked=False,
        repo=resolved_repo,
        issue_number=issue_number,
        issue_url=issue_url,
        branch=resolved_branch,
        commit_sha=_git_output(["git", "rev-parse", "HEAD"], store.root),
        remote_url=_git_output(["git", "config", "--get", "remote.origin.url"], store.root),
        command_summaries=commands,
        stdout=stdout,
        stderr=stderr,
        evidence={"body_path": str(body_path)},
    )


def create_github_pr_for_ticket(
    store: AriadneStore,
    ticket: BuildTicket,
    *,
    repo: str | None,
    base: str,
    head: str | None,
    draft: bool,
    confirm_write: bool,
) -> GitHubIntegrationResult:
    github_meta = ticket.metadata.get("github") if isinstance(ticket.metadata.get("github"), dict) else {}
    resolved_repo = repo or github_meta.get("repo") or infer_github_repo(store.root)
    issue = _int_or_none(github_meta.get("issue"))
    resolved_head = head or github_meta.get("branch") or _git_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], store.root)
    result_id = stable_id("github", ticket.id, "create_pr", resolved_repo, resolved_head, utc_now())
    if not confirm_write:
        return _blocked_result(
            result_id=result_id,
            ticket=ticket,
            operation="create_pr",
            reason="GitHub PR creation writes require --confirm-write",
            repo=resolved_repo,
            issue=issue,
            pr=None,
            branch=resolved_head,
        )
    gh_path = shutil.which("gh")
    if gh_path is None:
        return _blocked_result(
            result_id=result_id,
            ticket=ticket,
            operation="create_pr",
            reason="gh command is not installed",
            failure_reason=FailureReason.COMMAND_UNAVAILABLE,
            repo=resolved_repo,
            issue=issue,
            pr=None,
            branch=resolved_head,
        )
    if not resolved_repo or not resolved_head:
        return _blocked_result(
            result_id=result_id,
            ticket=ticket,
            operation="create_pr",
            reason="GitHub repo and head branch are required before PR creation",
            failure_reason=FailureReason.INVALID_RESOURCE,
            repo=resolved_repo,
            issue=issue,
            pr=None,
            branch=resolved_head,
        )

    body_path = _write_pr_body(store, ticket, issue)
    command = [
        gh_path,
        "pr",
        "create",
        "--repo",
        resolved_repo,
        "--base",
        base,
        "--head",
        resolved_head,
        "--title",
        f"[Ariadne] {ticket.key}: {ticket.title}",
        "--body-file",
        str(body_path),
    ]
    if draft:
        command.append("--draft")
    pr_result = _run(command, cwd=store.root)
    commands = [_redact_command(command)]
    if pr_result.returncode != 0:
        return _failed_result(
            result_id,
            ticket,
            "create_pr",
            resolved_repo,
            issue,
            None,
            resolved_head,
            commands,
            pr_result,
            store.root,
        )

    stdout = _redact_text(pr_result.stdout)
    stderr = _redact_text(pr_result.stderr)
    pr_url = _extract_pr_url(stdout)
    pr_number = _extract_pr_number(pr_url)
    github_meta = {
        **github_meta,
        "repo": resolved_repo,
        "issue": issue,
        "pr": pr_number,
        "branch": resolved_head,
        "base": base,
        "linked_at": utc_now(),
    }
    store.save_ticket(ticket.model_copy(deep=True, update={"metadata": ticket.metadata | {"github": github_meta}}))
    return GitHubIntegrationResult(
        id=result_id,
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        operation="create_pr",
        ok=True,
        blocked=False,
        repo=resolved_repo,
        issue_number=issue,
        pr_number=pr_number,
        pr_url=pr_url,
        branch=resolved_head,
        commit_sha=_git_output(["git", "rev-parse", "HEAD"], store.root),
        remote_url=_git_output(["git", "config", "--get", "remote.origin.url"], store.root),
        command_summaries=commands,
        stdout=stdout,
        stderr=stderr,
        evidence={"body_path": str(body_path), "base": base, "draft": draft},
    )


def github_status_for_ticket(
    store: AriadneStore,
    ticket: BuildTicket,
) -> GitHubIntegrationResult:
    github_meta = ticket.metadata.get("github") if isinstance(ticket.metadata.get("github"), dict) else {}
    repo = github_meta.get("repo") or infer_github_repo(store.root)
    issue = _int_or_none(github_meta.get("issue"))
    pr = _int_or_none(github_meta.get("pr"))
    branch = github_meta.get("branch") or _git_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], store.root)
    result_id = stable_id("github", ticket.id, "status", repo, issue, pr, branch, utc_now())
    gh_path = shutil.which("gh")
    if gh_path is None:
        return _blocked_result(
            result_id=result_id,
            ticket=ticket,
            operation="status",
            reason="gh command is not installed",
            failure_reason=FailureReason.COMMAND_UNAVAILABLE,
            repo=repo,
            issue=issue,
            pr=pr,
            branch=branch,
        )
    if not repo:
        return _blocked_result(
            result_id=result_id,
            ticket=ticket,
            operation="status",
            reason="GitHub repo is required before status read",
            failure_reason=FailureReason.INVALID_RESOURCE,
            repo=repo,
            issue=issue,
            pr=pr,
            branch=branch,
        )

    commands: list[str] = []
    issue_payload: dict[str, Any] = {}
    if issue:
        issue_payload, issue_result = _gh_json(
            [gh_path, "issue", "view", str(issue), "--repo", repo, "--json", "number,title,state,url"],
            store.root,
            commands,
        )
        if issue_result.returncode != 0:
            return _failed_result(result_id, ticket, "status", repo, issue, pr, branch, commands, issue_result, store.root)

    pr_payload: dict[str, Any] = {}
    checks_payload: list[Any] = []
    check_result: subprocess.CompletedProcess[str] | None = None
    pr_ref = str(pr) if pr else branch
    if pr_ref:
        pr_payload, pr_result = _gh_json(
            [
                gh_path,
                "pr",
                "view",
                pr_ref,
                "--repo",
                repo,
                "--json",
                "number,title,state,url,headRefName,headRefOid,baseRefName,mergeable,reviewDecision,statusCheckRollup",
            ],
            store.root,
            commands,
        )
        if pr_result.returncode != 0:
            return _failed_result(result_id, ticket, "status", repo, issue, pr, branch, commands, pr_result, store.root)
        pr = _int_or_none(pr_payload.get("number")) or pr
        check_ref = str(pr) if pr else pr_ref
        check_payload, check_result = _gh_checks_json(
            [
                gh_path,
                "pr",
                "checks",
                check_ref,
                "--repo",
                repo,
                "--json",
                "name,state,bucket,link,workflow,completedAt,startedAt",
            ],
            store.root,
            commands,
        )
        checks_payload = check_payload
        no_checks_reported = _is_no_checks_reported(check_result)
        if check_result.returncode not in (0, 8) and not no_checks_reported:
            return _failed_result(result_id, ticket, "status", repo, issue, pr, branch, commands, check_result, store.root)
    else:
        no_checks_reported = False

    return GitHubIntegrationResult(
        id=result_id,
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        operation="status",
        ok=True,
        blocked=False,
        repo=repo,
        issue_number=issue,
        issue_url=_string(issue_payload.get("url")),
        pr_number=pr,
        pr_url=_string(pr_payload.get("url")),
        branch=_string(pr_payload.get("headRefName")) or branch,
        commit_sha=_string(pr_payload.get("headRefOid")) or _git_output(["git", "rev-parse", "HEAD"], store.root),
        remote_url=_git_output(["git", "config", "--get", "remote.origin.url"], store.root),
        command_summaries=commands,
        stderr=_redact_text(check_result.stderr) if check_result else "",
        evidence={
            "issue": issue_payload,
            "pr": pr_payload,
            "checks": checks_payload,
            "checks_status": "no_checks_reported" if no_checks_reported else "captured",
        },
    )


def sync_ticket_with_github(
    store: AriadneStore,
    ticket: BuildTicket,
    *,
    confirm_write: bool,
) -> GitHubIntegrationResult:
    github_meta = ticket.metadata.get("github") if isinstance(ticket.metadata.get("github"), dict) else {}
    repo = github_meta.get("repo") or infer_github_repo(store.root)
    issue = _int_or_none(github_meta.get("issue"))
    pr = _int_or_none(github_meta.get("pr"))
    branch = github_meta.get("branch") or _git_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], store.root)
    result_id = stable_id("github", ticket.id, "sync", repo, issue, pr, utc_now())
    if not confirm_write:
        return _blocked_result(
            result_id=result_id,
            ticket=ticket,
            operation="sync",
            reason="GitHub sync writes require --confirm-write",
            repo=repo,
            issue=issue,
            pr=pr,
            branch=branch,
        )
    gh_path = shutil.which("gh")
    if gh_path is None:
        return _blocked_result(
            result_id=result_id,
            ticket=ticket,
            operation="sync",
            reason="gh command is not installed",
            failure_reason=FailureReason.COMMAND_UNAVAILABLE,
            repo=repo,
            issue=issue,
            pr=pr,
            branch=branch,
        )
    if not repo or not issue:
        return _blocked_result(
            result_id=result_id,
            ticket=ticket,
            operation="sync",
            reason="GitHub repo and issue link are required before sync",
            failure_reason=FailureReason.INVALID_RESOURCE,
            repo=repo,
            issue=issue,
            pr=pr,
            branch=branch,
        )

    commands: list[str] = []
    issue_payload, issue_result = _gh_json(
        [gh_path, "issue", "view", str(issue), "--repo", repo, "--json", "number,title,state,url"],
        store.root,
        commands,
    )
    if issue_result.returncode != 0:
        return _failed_result(
            result_id,
            ticket,
            "sync",
            repo,
            issue,
            pr,
            branch,
            commands,
            issue_result,
            store.root,
        )

    pr_payload: dict[str, Any] = {}
    pr_result = None
    if pr:
        pr_payload, pr_result = _gh_json(
            [
                gh_path,
                "pr",
                "view",
                str(pr),
                "--repo",
                repo,
                "--json",
                "number,title,state,url,headRefName,headRefOid",
            ],
            store.root,
            commands,
        )
        if pr_result.returncode != 0:
            return _failed_result(
                result_id,
                ticket,
                "sync",
                repo,
                issue,
                pr,
                branch,
                commands,
                pr_result,
                store.root,
            )

    body_path = _write_comment_body(store, ticket, issue_payload, pr_payload)
    comment_result = _run(
        [gh_path, "issue", "comment", str(issue), "--repo", repo, "--body-file", str(body_path)],
        cwd=store.root,
    )
    commands.append(_redact_command([gh_path, "issue", "comment", str(issue), "--repo", repo, "--body-file", str(body_path)]))
    if comment_result.returncode != 0:
        return _failed_result(
            result_id,
            ticket,
            "sync",
            repo,
            issue,
            pr,
            branch,
            commands,
            comment_result,
            store.root,
        )

    stdout = _redact_text(comment_result.stdout)
    stderr = _redact_text(comment_result.stderr)
    return GitHubIntegrationResult(
        id=result_id,
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        operation="sync",
        ok=True,
        blocked=False,
        repo=repo,
        issue_number=issue,
        issue_url=_string(issue_payload.get("url")),
        pr_number=pr,
        pr_url=_string(pr_payload.get("url")),
        branch=_string(pr_payload.get("headRefName")) or branch,
        commit_sha=_string(pr_payload.get("headRefOid")) or _git_output(["git", "rev-parse", "HEAD"], store.root),
        remote_url=_git_output(["git", "config", "--get", "remote.origin.url"], store.root),
        comment_url=stdout.strip() or None,
        command_summaries=commands,
        stdout=stdout,
        stderr=stderr,
        evidence={"issue": issue_payload, "pr": pr_payload},
    )


def infer_github_repo(root: Path) -> str | None:
    remote = _git_output(["git", "config", "--get", "remote.origin.url"], root)
    if not remote:
        return None
    return parse_github_repo(remote)


def parse_github_repo(remote_url: str) -> str | None:
    text = remote_url.strip()
    patterns = [
        r"github\.com[:/](?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)(?:\.git)?$",
        r"https?://github\.com/(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)(?:\.git)?$",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return f"{match.group('owner')}/{match.group('repo')}"
    return None


def _gh_json(command: list[str], cwd: Path, commands: list[str]) -> tuple[dict[str, Any], subprocess.CompletedProcess[str]]:
    result = _run(command, cwd=cwd)
    commands.append(_redact_command(command))
    if result.returncode != 0:
        return {}, result
    try:
        payload = json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        payload = {"stdout": _redact_text(result.stdout)}
    return payload if isinstance(payload, dict) else {"stdout": payload}, result


def _gh_checks_json(command: list[str], cwd: Path, commands: list[str]) -> tuple[list[Any], subprocess.CompletedProcess[str]]:
    result = _run(command, cwd=cwd)
    commands.append(_redact_command(command))
    try:
        payload = json.loads(result.stdout) if result.stdout.strip() else []
    except json.JSONDecodeError:
        payload = [{"stdout": _redact_text(result.stdout)}]
    return payload if isinstance(payload, list) else [payload], result


def _write_comment_body(
    store: AriadneStore,
    ticket: BuildTicket,
    issue_payload: dict[str, Any],
    pr_payload: dict[str, Any],
) -> Path:
    workspace = store.github_integrations_dir / ticket.key
    workspace.mkdir(parents=True, exist_ok=True)
    path = workspace / f"{ticket.id}_github_comment.md"
    issue_title = issue_payload.get("title", "")
    pr_line = (
        f"- PR: #{pr_payload.get('number')} {pr_payload.get('title', '')}\n"
        if pr_payload
        else ""
    )
    path.write_text(
        f"### Ariadne sync for {ticket.key}\n\n"
        f"- Ticket: {ticket.key} - {ticket.title}\n"
        f"- Issue: #{issue_payload.get('number')} {issue_title}\n"
        f"{pr_line}"
        f"- Status: `{ticket.status.value}`\n\n"
        "Ariadne recorded this sync from the local ticket-centered Agent Workbench.\n",
        encoding="utf-8",
    )
    return path


def _write_issue_body(store: AriadneStore, ticket: BuildTicket) -> Path:
    workspace = store.github_integrations_dir / ticket.key
    workspace.mkdir(parents=True, exist_ok=True)
    path = workspace / f"{ticket.id}_github_issue.md"
    path.write_text(
        f"### Ariadne ticket {ticket.key}\n\n"
        f"- Ticket: `{ticket.key}`\n"
        f"- Local ticket id: `{ticket.id}`\n"
        f"- Status: `{ticket.status.value}`\n"
        f"- Source type: `{ticket.source_type}`\n"
        f"- Source ref: `{ticket.source_ref}`\n\n"
        "This issue was created by Ariadne's gated GitHub integration from the "
        "local ticket-centered Agent Workbench.\n\n"
        "Description:\n\n"
        f"{ticket.description.strip()}\n",
        encoding="utf-8",
    )
    return path


def _write_pr_body(store: AriadneStore, ticket: BuildTicket, issue: int | None) -> Path:
    workspace = store.github_integrations_dir / ticket.key
    workspace.mkdir(parents=True, exist_ok=True)
    path = workspace / f"{ticket.id}_github_pr.md"
    close_line = f"\nCloses #{issue}\n" if issue else ""
    path.write_text(
        f"### Ariadne PR for {ticket.key}\n\n"
        f"- Ticket: `{ticket.key}`\n"
        f"- Local ticket id: `{ticket.id}`\n"
        f"- Status: `{ticket.status.value}`\n"
        f"- Source type: `{ticket.source_type}`\n\n"
        "This PR was created by Ariadne's gated GitHub integration after local "
        "verification evidence was recorded.\n"
        f"{close_line}\n"
        "Summary:\n\n"
        f"{ticket.description.strip()}\n",
        encoding="utf-8",
    )
    return path


def _failed_result(
    result_id: str,
    ticket: BuildTicket,
    operation: str,
    repo: str | None,
    issue: int | None,
    pr: int | None,
    branch: str | None,
    commands: list[str],
    process: subprocess.CompletedProcess[str],
    root: Path,
) -> GitHubIntegrationResult:
    stdout = _redact_text(process.stdout)
    stderr = _redact_text(process.stderr)
    return GitHubIntegrationResult(
        id=result_id,
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        operation=operation,
        ok=False,
        blocked=False,
        failure_reason=_classify_failure(stdout, stderr),
        reason=stderr or stdout or f"gh exited {process.returncode}",
        repo=repo,
        issue_number=issue,
        pr_number=pr,
        branch=branch,
        commit_sha=_git_output(["git", "rev-parse", "HEAD"], root),
        command_summaries=commands,
        stdout=stdout,
        stderr=stderr,
    )


def _blocked_result(
    *,
    result_id: str,
    ticket: BuildTicket,
    operation: str,
    reason: str,
    failure_reason: FailureReason = FailureReason.EXTERNAL_EXECUTION_BLOCKED,
    repo: str | None,
    issue: int | None,
    pr: int | None,
    branch: str | None,
) -> GitHubIntegrationResult:
    return GitHubIntegrationResult(
        id=result_id,
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        operation=operation,
        ok=False,
        blocked=True,
        failure_reason=failure_reason,
        reason=_redact_text(reason),
        repo=repo,
        issue_number=issue,
        pr_number=pr,
        branch=branch,
    )


def _classify_failure(stdout: str, stderr: str) -> FailureReason:
    text = f"{stdout}\n{stderr}".lower()
    if any(marker in text for marker in ["auth", "login", "unauthorized", "forbidden"]):
        return FailureReason.AUTHENTICATION_FAILED
    if any(marker in text for marker in ["rate limit", "quota", "too many requests"]):
        return FailureReason.QUOTA_EXCEEDED
    if "timed out" in text or "timeout" in text:
        return FailureReason.TIMEOUT
    return FailureReason.AGENT_ERROR


def _is_no_checks_reported(process: subprocess.CompletedProcess[str]) -> bool:
    return "no checks reported" in f"{process.stdout}\n{process.stderr}".lower()


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)


def _git_output(command: list[str], root: Path) -> str | None:
    result = _run(command, cwd=root)
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _redact_command(command: list[str]) -> str:
    return _redact_text(shlex.join(command))


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
    redacted = re.sub(r"gh[pousr]_[A-Za-z0-9_]{20,}", "[REDACTED]", redacted)
    return redacted


def _redact_url(value: str | None) -> str | None:
    if not value:
        return None
    text = _redact_text(value.strip())
    return re.sub(r"(https?://)[^/@\s:]+:[^/@\s]+@", r"\1[REDACTED]:[REDACTED]@", text)


def _redact_dynamic_secrets(text: str, secrets: list[str]) -> str:
    redacted = _redact_text(text)
    for secret in sorted({secret for secret in secrets if secret}, key=len, reverse=True):
        redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


def _url_userinfo_secrets(*values: str | None) -> list[str]:
    secrets: list[str] = []
    for value in values:
        if not value:
            continue
        match = re.search(r"https?://(?P<userinfo>[^/@\s]+)@", value)
        if not match:
            continue
        userinfo = match.group("userinfo")
        secrets.extend(part for part in userinfo.split(":", 1) if part)
    return secrets


def _first_line(text: str) -> str:
    return next((line.strip() for line in text.splitlines() if line.strip()), "")


def _extract_issue_url(stdout: str) -> str | None:
    match = re.search(r"https://github\.com/[^\s]+/issues/\d+", stdout)
    return match.group(0) if match else None


def _extract_issue_number(issue_url: str | None) -> int | None:
    if not issue_url:
        return None
    match = re.search(r"/issues/(?P<number>\d+)$", issue_url)
    return int(match.group("number")) if match else None


def _extract_pr_url(stdout: str) -> str | None:
    match = re.search(r"https://github\.com/[^\s]+/pull/\d+", stdout)
    return match.group(0) if match else None


def _extract_pr_number(pr_url: str | None) -> int | None:
    if not pr_url:
        return None
    match = re.search(r"/pull/(?P<number>\d+)$", pr_url)
    return int(match.group("number")) if match else None


def _secret_values() -> list[str]:
    values = []
    for name, value in os.environ.items():
        upper = name.upper()
        if not value or len(value) < 4:
            continue
        if any(marker in upper for marker in ["SECRET", "TOKEN", "API_KEY", "PASSWORD"]):
            values.append(value)
    return sorted(set(values), key=len, reverse=True)


def _int_or_none(value: object) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None
