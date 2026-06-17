from __future__ import annotations

import json
from pathlib import Path
import subprocess

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import (
    ArtifactType,
    BackendSmokeEvidence,
    BuildDecision,
    BuildPacket,
    Evidence,
    ExecutionResult,
    FeishuWriteResult,
    GitHubIntegrationResult,
    ReviewReport,
    ReviewVerdict,
)
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def _seed_release_packet(root: Path) -> None:
    evidence_dir = root / ".ariadne" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "release_evidence_packet.json").write_text(
        json.dumps(
            {
                "id": "release_evidence_test",
                "evidence_refs": {
                    "integration_doctor": str(root / ".ariadne" / "doctor" / "integrations.json"),
                    "runtime_capabilities": str(root / ".ariadne" / "runtimes" / "capability_snapshot.json"),
                    "feishu_integrations": str(root / ".ariadne" / "integrations" / "feishu"),
                    "github_integrations": str(root / ".ariadne" / "integrations" / "github"),
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _seed_full_github_product_evidence(store: AriadneStore) -> None:
    store.save_github_integration_result(
        GitHubIntegrationResult(
            id="github_issue_success",
            ticket_id="ticket_ari_003",
            ticket_key="ARI-003",
            operation="create_issue",
            ok=True,
            blocked=False,
            repo="owner/repo",
            issue_number=42,
            issue_url="https://github.com/owner/repo/issues/42",
            branch="codex/product",
            commit_sha="abc123",
        )
    )
    store.save_github_integration_result(
        GitHubIntegrationResult(
            id="github_pr_success",
            ticket_id="ticket_ari_003",
            ticket_key="ARI-003",
            operation="create_pr",
            ok=True,
            blocked=False,
            repo="owner/repo",
            issue_number=42,
            issue_url="https://github.com/owner/repo/issues/42",
            pr_number=11,
            pr_url="https://github.com/owner/repo/pull/11",
            branch="codex/product",
            commit_sha="abc123",
        )
    )
    store.save_github_integration_result(
        GitHubIntegrationResult(
            id="github_sync_success",
            ticket_id="ticket_ari_003",
            ticket_key="ARI-003",
            operation="sync",
            ok=True,
            blocked=False,
            repo="owner/repo",
            issue_number=42,
            issue_url="https://github.com/owner/repo/issues/42",
            pr_number=11,
            pr_url="https://github.com/owner/repo/pull/11",
            comment_url="https://github.com/owner/repo/issues/42#issuecomment-1",
            branch="codex/product",
            commit_sha="abc123",
        )
    )
    store.save_github_integration_result(
        GitHubIntegrationResult(
            id="github_status_success",
            ticket_id="ticket_ari_003",
            ticket_key="ARI-003",
            operation="status",
            ok=True,
            blocked=False,
            repo="owner/repo",
            issue_number=42,
            issue_url="https://github.com/owner/repo/issues/42",
            pr_number=11,
            pr_url="https://github.com/owner/repo/pull/11",
            branch="codex/product",
            commit_sha="abc123",
            evidence={"checks_status": "captured"},
        )
    )


def _seed_llm_agent_product_evidence(store: AriadneStore) -> None:
    llm_packet = BuildPacket(
        id="packet_llm_success",
        ticket_id="ticket_ari_003",
        source_summary="LLM planner summarized the source.",
        insight="The ticket requires code work.",
        evidence=[
            Evidence(
                id="evidence_llm_success",
                source_ref="source_llm_success",
                quote_or_summary="Evidence extracted by LLM planner.",
                location="fixture:1",
            )
        ],
        project_relevance="Relevant to the local workbench.",
        build_decision=BuildDecision.CODE_TASK,
        tasks=["Implement the requested change."],
        acceptance_criteria=["The change is verified."],
        affected_modules=["ariadne_ltb/example.py"],
        metadata={"planner_mode": "llm"},
    )
    store.save_build_packet(llm_packet)
    store.write_artifact(
        llm_packet.ticket_id,
        "run_llm_planner",
        ArtifactType.BUILD_PACKET,
        "build_packet.json",
        llm_packet.model_dump_json(indent=2) + "\n",
        "Planner Build Packet",
        metadata={"build_packet_id": llm_packet.id, "planner_mode": "llm"},
    )
    # A later deterministic run may overwrite the current packet record. Product
    # evidence must still recognize the historical LLM planner artifact.
    store.save_build_packet(
        BuildPacket(
            id="packet_llm_success",
            ticket_id="ticket_ari_003",
            source_summary="Deterministic planner overwrote the current packet.",
            insight="The ticket requires code work.",
            evidence=[
                Evidence(
                    id="evidence_deterministic_success",
                    source_ref="source_deterministic_success",
                    quote_or_summary="Evidence extracted by deterministic planner.",
                    location="fixture:1",
                )
            ],
            project_relevance="Relevant to the local workbench.",
            build_decision=BuildDecision.CODE_TASK,
            tasks=["Implement the requested change."],
            acceptance_criteria=["The change is verified."],
            affected_modules=["ariadne_ltb/example.py"],
            metadata={"planner_mode": "deterministic"},
        )
    )
    store.save_review_report(
        ReviewReport(
            id="review_llm_success",
            ticket_id="ticket_ari_003",
            verdict=ReviewVerdict.PASS,
            reviewer_mode="llm",
            risk_score=0.1,
            passed_checks=["LLM reviewer completed"],
        )
    )
    store.write_artifact(
        "ticket_ari_003",
        "run_llm_backlog",
        ArtifactType.NEXT_TICKETS,
        "llm_next_tickets.json",
        json.dumps(
            {
                "source_ticket_id": "ticket_ari_003",
                "planner": "llm",
                "blocked": False,
                "next_tickets": [],
            }
        )
        + "\n",
        "LLM-generated backlog delta suggestions",
        metadata={"source": "llm_backlog_planner", "planner": "llm", "blocked": False},
    )
    for role in ["build_lead", "knowledge", "memory"]:
        store.write_artifact(
            "ticket_ari_003",
            f"run_llm_{role}",
            ArtifactType.LLM_AGENT_RESULT,
            f"llm_{role}.json",
            json.dumps(
                {
                    "role": role,
                    "schema_name": f"ariadne_{role}_agent_result",
                    "succeeded": True,
                    "output_json": {
                        "summary": f"{role} completed.",
                        "decision": "continue",
                        "evidence": ["fixture evidence"],
                        "risks": [],
                        "recommended_actions": ["continue production path"],
                    },
                    "provider": "deepseek",
                    "model": "deepseek-v4-pro",
                    "usage": {"total_tokens": 10},
                }
            )
            + "\n",
            f"DeepSeek LLM {role} agent result",
            metadata={
                "llm_role": role,
                "provider": "deepseek",
                "model": "deepseek-v4-pro",
                "succeeded": True,
                "schema_name": f"ariadne_{role}_agent_result",
            },
        )


def test_doctor_secrets_does_not_print_secret_values(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "do-not-leak-deepseek")
    monkeypatch.setenv("FEISHU_APP_SECRET", "do-not-leak-feishu")

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "doctor", "secrets"])

    assert result.exit_code == 0, result.output
    assert "DEEPSEEK_API_KEY: set" in result.output
    assert "FEISHU_APP_SECRET: set" in result.output
    assert "secret scan:" in result.output
    assert "do-not-leak" not in result.output


def test_doctor_v1_reports_local_readiness(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    runner = CliRunner()
    runner.invoke(app, ["--root", str(tmp_path), "ticket", "assign", "ARI-003", "--to", "fake-codex"])
    runner.invoke(app, ["--root", str(tmp_path), "daemon", "run-once"])
    runner.invoke(app, ["--root", str(tmp_path), "export", "board"])

    result = runner.invoke(app, ["--root", str(tmp_path), "doctor", "v1"])

    assert result.exit_code == 0, result.output
    assert "agent profiles: ok" in result.output
    assert "backend capability: ok" in result.output
    assert "source fixtures: ok" in result.output
    assert "board: ok" in result.output
    assert "safety gates: ok" in result.output
    assert "secret scan:" in result.output


def test_doctor_integrations_reports_readiness_without_secret_values(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "do-not-leak-deepseek")
    monkeypatch.setenv(
        "ARIADNE_LLM_BASE_URL",
        "https://user:do-not-leak-url-password@proxy.example.com:8443/v1?token=do-not-leak-url-token",
    )
    monkeypatch.setenv("FEISHU_APP_SECRET", "do-not-leak-feishu")
    monkeypatch.setenv("GITHUB_TOKEN", "do-not-leak-github")
    monkeypatch.setenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", "1")
    monkeypatch.setenv("FEISHU_ENABLE_WRITE", "1")

    def fake_which(command: str) -> str | None:
        return {
            "codex": "/usr/local/bin/codex",
            "claude": "/usr/local/bin/claude",
            "lark-cli": "/usr/local/bin/lark-cli",
            "gh": "/usr/local/bin/gh",
        }.get(command)

    monkeypatch.setattr("ariadne_ltb.runtime.shutil.which", fake_which)
    monkeypatch.setattr("ariadne_ltb.doctor.shutil.which", fake_which)
    monkeypatch.setattr("ariadne_ltb.github_integration.shutil.which", fake_which)
    monkeypatch.setattr(
        "ariadne_ltb.doctor.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "", ""),
    )
    monkeypatch.setattr(
        "ariadne_ltb.github_integration.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "ok\n", ""),
    )

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "doctor", "integrations"])

    assert result.exit_code == 0, result.output
    assert "Integration doctor: ok" in result.output
    assert "DeepSeek API key: set" in result.output
    assert "CodexBackend command: found /usr/local/bin/codex" in result.output
    assert "ClaudeCodeBackend command: found /usr/local/bin/claude" in result.output
    assert "Feishu lark-cli command: found /usr/local/bin/lark-cli" in result.output
    assert "GitHub gh command: found /usr/local/bin/gh" in result.output
    assert "GitHub auth status: ok" in result.output
    assert "GitHub git transport: ok" in result.output
    assert "DeepSeek base URL: https://proxy.example.com:8443" in result.output
    assert "do-not-leak" not in result.output
    assert "user:" not in result.output

    snapshot_path = tmp_path / ".ariadne" / "doctor" / "integrations.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["llm"]["deepseek_api_key"] == "set"
    assert snapshot["llm"]["base_url"] == "https://proxy.example.com:8443"
    assert snapshot["feishu"]["FEISHU_APP_SECRET"] == "set"
    assert snapshot["github"]["GITHUB_TOKEN"] == "set"
    assert snapshot["github"]["git_transport"]["status"] == "ok"
    assert "do-not-leak" not in snapshot_path.read_text(encoding="utf-8")
    assert "user:" not in snapshot_path.read_text(encoding="utf-8")


def test_doctor_integrations_json_output_is_machine_readable(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("FEISHU_ENABLE_WRITE", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr("ariadne_ltb.runtime.shutil.which", lambda command: None)
    monkeypatch.setattr("ariadne_ltb.doctor.shutil.which", lambda command: None)

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "doctor", "integrations", "--json"])

    assert result.exit_code == 0, result.output
    snapshot = json.loads(result.output)
    assert snapshot["llm"]["provider"] == "deepseek"
    assert snapshot["llm"]["deepseek_api_key"] == "unset"
    assert snapshot["coding_backends"]["codex"]["available"] is False
    assert snapshot["github"]["auth_status"] == "unavailable"
    assert snapshot["github"]["git_transport"]["status"] in {"no_remote", "failed"}
    assert (tmp_path / ".ariadne" / "doctor" / "integrations.json").exists()


def test_doctor_integrations_reports_direct_git_transport_when_proxy_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    def fake_which(command: str) -> str | None:
        return {
            "codex": "/usr/local/bin/codex",
            "claude": "/usr/local/bin/claude",
            "lark-cli": "/usr/local/bin/lark-cli",
            "gh": "/usr/local/bin/gh",
        }.get(command)

    def fake_github_run(command, **kwargs):  # type: ignore[no-untyped-def]
        if command[:3] == ["git", "config", "--get"] and command[-1] == "remote.origin.url":
            return subprocess.CompletedProcess(command, 0, "https://github.com/owner/repo.git\n", "")
        if command[:3] == ["git", "config", "--get"] and command[-1] in {"http.proxy", "https.proxy"}:
            return subprocess.CompletedProcess(
                command,
                0,
                "http://user:proxy-secret@127.0.0.1:7890\n",
                "",
            )
        if command[:2] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(command, 0, "codex/product\n", "")
        if command[:5] == ["git", "-c", "http.proxy=", "-c", "https.proxy="]:
            return subprocess.CompletedProcess(command, 0, "abc123\trefs/heads/codex/product\n", "")
        if command[:3] == ["git", "ls-remote", "--heads"]:
            return subprocess.CompletedProcess(command, 128, "", "SSL_ERROR_SYSCALL proxy-secret")
        return subprocess.CompletedProcess(command, 1, "", f"unexpected command: {command}")

    monkeypatch.setattr("ariadne_ltb.runtime.shutil.which", fake_which)
    monkeypatch.setattr("ariadne_ltb.doctor.shutil.which", fake_which)
    monkeypatch.setattr("ariadne_ltb.github_integration.shutil.which", fake_which)
    monkeypatch.setattr(
        "ariadne_ltb.doctor.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "", ""),
    )
    monkeypatch.setattr("ariadne_ltb.github_integration.subprocess.run", fake_github_run)

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "doctor", "integrations"])

    assert result.exit_code == 0, result.output
    assert "GitHub git transport: failed" in result.output
    assert "GitHub git transport without proxy: ok" in result.output
    assert "GitHub git transport suggested fix: Configured git proxy failed" in result.output
    assert "proxy-secret" not in result.output
    snapshot = json.loads((tmp_path / ".ariadne" / "doctor" / "integrations.json").read_text())
    assert snapshot["github"]["git_transport"]["status"] == "failed"
    assert snapshot["github"]["git_transport"]["direct_without_proxy"]["status"] == "ok"
    assert "proxy-secret" not in json.dumps(snapshot)


def test_doctor_product_reports_acceptance_readiness_without_external_writes(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "do-not-leak-deepseek")
    monkeypatch.delenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", raising=False)
    monkeypatch.delenv("FEISHU_ENABLE_WRITE", raising=False)

    evidence_dir = tmp_path / ".ariadne" / "evidence"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "release_evidence_packet.json").write_text(
        json.dumps(
            {
                "id": "release_evidence_test",
                "evidence_refs": {
                    "integration_doctor": str(tmp_path / ".ariadne" / "doctor" / "integrations.json"),
                    "runtime_capabilities": str(
                        tmp_path / ".ariadne" / "runtimes" / "capability_snapshot.json"
                    ),
                    "feishu_integrations": str(tmp_path / ".ariadne" / "integrations" / "feishu"),
                    "github_integrations": str(tmp_path / ".ariadne" / "integrations" / "github"),
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    def fake_which(command: str) -> str | None:
        return {
            "codex": "/usr/local/bin/codex",
            "claude": "/usr/local/bin/claude",
            "lark-cli": "/usr/local/bin/lark-cli",
            "gh": "/usr/local/bin/gh",
        }.get(command)

    def fake_github_run(command, **kwargs):  # type: ignore[no-untyped-def]
        if command[:3] == ["gh", "auth", "status"]:
            return subprocess.CompletedProcess(command, 0, "", "")
        if command[:3] == ["git", "config", "--get"] and command[-1] == "remote.origin.url":
            return subprocess.CompletedProcess(command, 0, "https://github.com/owner/repo.git\n", "")
        if command[:3] == ["git", "config", "--get"]:
            return subprocess.CompletedProcess(command, 1, "", "")
        if command[:2] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(command, 0, "codex/product\n", "")
        if command[:3] == ["git", "ls-remote", "--heads"]:
            return subprocess.CompletedProcess(command, 0, "abc123\trefs/heads/codex/product\n", "")
        return subprocess.CompletedProcess(command, 1, "", f"unexpected command: {command}")

    monkeypatch.setattr("ariadne_ltb.runtime.shutil.which", fake_which)
    monkeypatch.setattr("ariadne_ltb.doctor.shutil.which", fake_which)
    monkeypatch.setattr("ariadne_ltb.github_integration.shutil.which", fake_which)
    monkeypatch.setattr(
        "ariadne_ltb.doctor.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "", ""),
    )
    monkeypatch.setattr("ariadne_ltb.github_integration.subprocess.run", fake_github_run)

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "doctor", "product"])

    assert result.exit_code == 0, result.output
    assert "Product readiness: action_required" in result.output
    assert "Production acceptance: action_required" in result.output
    assert "Run gates: action_required" in result.output
    assert "deepseek_llm: ready" in result.output
    assert "codex_backend: ready" in result.output
    assert "github_git_transport: ready" in result.output
    assert "external_execution_gate: action_required" in result.output
    assert "feishu_write_gate: action_required" in result.output
    assert "real_codex_execution_evidence: action_required" in result.output
    assert "real_claude_execution_evidence: action_required" in result.output
    assert "real_feishu_write_evidence: action_required" in result.output
    assert "real_github_write_evidence: action_required" in result.output
    assert "do-not-leak" not in result.output

    snapshot_path = tmp_path / ".ariadne" / "doctor" / "product_readiness.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["overall_status"] == "action_required"
    assert snapshot["production_acceptance_status"] == "action_required"
    assert snapshot["run_gate_status"] == "action_required"
    assert snapshot["release_evidence_packet"]["has_integration_refs"] is True
    statuses = {check["name"]: check["status"] for check in snapshot["checks"]}
    assert statuses["release_evidence_packet"] == "ready"
    assert statuses["integration_evidence_refs"] == "ready"
    assert statuses["external_execution_gate"] == "action_required"
    assert statuses["real_codex_execution_evidence"] == "action_required"
    assert statuses["real_claude_execution_evidence"] == "action_required"
    assert statuses["real_feishu_write_evidence"] == "action_required"
    assert statuses["real_github_write_evidence"] == "action_required"
    assert statuses["real_github_issue_evidence"] == "action_required"
    assert statuses["real_github_pr_evidence"] == "action_required"
    assert statuses["real_github_comment_evidence"] == "action_required"
    assert statuses["real_github_status_evidence"] == "action_required"
    assert statuses["real_llm_agent_evidence"] == "action_required"
    assert "do-not-leak" not in snapshot_path.read_text(encoding="utf-8")

    required = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "doctor", "product", "--require-acceptance-ready"],
    )
    assert required.exit_code == 2, required.output
    assert "requirement failed: production acceptance is action_required, expected ready" in required.output


def test_doctor_product_marks_real_success_evidence_ready(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "do-not-leak-deepseek")
    monkeypatch.setenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", "1")
    monkeypatch.setenv("FEISHU_ENABLE_WRITE", "1")

    store = AriadneStore(tmp_path)
    _seed_release_packet(tmp_path)
    store.save_execution_result(
        ExecutionResult(
            id="exec_codex_success",
            ticket_id="ticket_ari_003",
            backend_name="codex",
            dry_run=False,
            blocked=False,
            command="codex exec --cd /repo --prompt-file handoff.md",
            exit_code=0,
            changed_files=["demo_todo/cli.py"],
            test_command="pytest",
            test_exit_code=0,
        )
    )
    store.save_execution_result(
        ExecutionResult(
            id="exec_claude_success",
            ticket_id="ticket_ari_003",
            backend_name="claude-code",
            dry_run=False,
            blocked=False,
            command="claude --print < handoff.md",
            exit_code=0,
            changed_files=["tests/test_cli.py"],
            test_command="pytest",
            test_exit_code=0,
        )
    )
    store.save_backend_smoke_evidence(
        BackendSmokeEvidence(
            id="backend_smoke_codex_success",
            backend_name="codex",
            ticket_id="ticket_ari_003",
            ticket_key="ARI-003",
            assignment_id="assignment_codex_success",
            assignment_status="done",
            succeeded=True,
            execution_result_id="exec_codex_success",
            exit_code=0,
            changed_files=["demo_todo/cli.py"],
            test_command="pytest",
            test_exit_code=0,
            review_verdict="pass",
            handoff_file=".ariadne/handoffs/ARI-003.md",
            board_path=".ariadne/board/index.md",
            memory_path=".ariadne/memory/tickets/ticket_ari_003.json",
            feishu_plan_path=".ariadne/feishu_plans/feishu_plan.json",
            next_tickets_path=".ariadne/artifacts/ticket_ari_003/next_tickets.json",
            external_execution_enabled=True,
            confirm_execution=True,
        )
    )
    store.save_backend_smoke_evidence(
        BackendSmokeEvidence(
            id="backend_smoke_claude_success",
            backend_name="claude-code",
            ticket_id="ticket_ari_003",
            ticket_key="ARI-003",
            assignment_id="assignment_claude_success",
            assignment_status="done",
            succeeded=True,
            execution_result_id="exec_claude_success",
            exit_code=0,
            changed_files=["tests/test_cli.py"],
            test_command="pytest",
            test_exit_code=0,
            review_verdict="pass",
            handoff_file=".ariadne/handoffs/ARI-003.md",
            external_execution_enabled=True,
            confirm_execution=True,
        )
    )
    store.save_feishu_write_result(
        FeishuWriteResult(
            id="feishu_success",
            ticket_id="ticket_ari_003",
            ticket_key="ARI-003",
            plan_id="feishu_plan",
            ok=True,
            blocked=False,
            dry_run=False,
            command="lark-cli docs create @content.md",
            returncode=0,
            document_id="doc_123",
            document_url="https://example.feishu.cn/docx/doc_123",
            operation_summary="Created Feishu doc.",
        )
    )
    _seed_llm_agent_product_evidence(store)
    _seed_full_github_product_evidence(store)

    def fake_which(command: str) -> str | None:
        return {
            "codex": "/usr/local/bin/codex",
            "claude": "/usr/local/bin/claude",
            "lark-cli": "/usr/local/bin/lark-cli",
            "gh": "/usr/local/bin/gh",
        }.get(command)

    def fake_github_run(command, **kwargs):  # type: ignore[no-untyped-def]
        if command[:3] == ["gh", "auth", "status"]:
            return subprocess.CompletedProcess(command, 0, "", "")
        if command[:3] == ["git", "config", "--get"] and command[-1] == "remote.origin.url":
            return subprocess.CompletedProcess(command, 0, "https://github.com/owner/repo.git\n", "")
        if command[:3] == ["git", "config", "--get"]:
            return subprocess.CompletedProcess(command, 1, "", "")
        if command[:2] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(command, 0, "codex/product\n", "")
        if command[:3] == ["git", "ls-remote", "--heads"]:
            return subprocess.CompletedProcess(command, 0, "abc123\trefs/heads/codex/product\n", "")
        return subprocess.CompletedProcess(command, 1, "", f"unexpected command: {command}")

    monkeypatch.setattr("ariadne_ltb.runtime.shutil.which", fake_which)
    monkeypatch.setattr("ariadne_ltb.doctor.shutil.which", fake_which)
    monkeypatch.setattr("ariadne_ltb.github_integration.shutil.which", fake_which)
    monkeypatch.setattr(
        "ariadne_ltb.doctor.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "", ""),
    )
    monkeypatch.setattr("ariadne_ltb.github_integration.subprocess.run", fake_github_run)

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "doctor", "product"])

    assert result.exit_code == 0, result.output
    assert "Product readiness: ready" in result.output
    assert "Production acceptance: ready" in result.output
    assert "Run gates: ready" in result.output
    snapshot = json.loads(
        (tmp_path / ".ariadne" / "doctor" / "product_readiness.json").read_text(encoding="utf-8")
    )
    assert snapshot["production_acceptance_status"] == "ready"
    assert snapshot["run_gate_status"] == "ready"
    statuses = {check["name"]: check["status"] for check in snapshot["checks"]}
    assert statuses["real_codex_execution_evidence"] == "ready"
    assert statuses["real_llm_agent_evidence"] == "ready"
    assert statuses["real_claude_execution_evidence"] == "ready"
    assert statuses["real_feishu_write_evidence"] == "ready"
    assert statuses["real_github_write_evidence"] == "ready"
    assert statuses["real_github_issue_evidence"] == "ready"
    assert statuses["real_github_pr_evidence"] == "ready"
    assert statuses["real_github_comment_evidence"] == "ready"
    assert statuses["real_github_status_evidence"] == "ready"
    assert snapshot["real_success_evidence"]["codex"]["id"] == "backend_smoke_codex_success"
    assert snapshot["real_success_evidence"]["codex"]["source"] == "backend_smoke"
    assert snapshot["real_success_evidence"]["claude_code"]["id"] == "backend_smoke_claude_success"
    assert snapshot["real_success_evidence"]["llm_agents"]["operations"] == {
        "backlog": True,
        "build_lead": True,
        "knowledge": True,
        "memory": True,
        "planner": True,
        "reviewer": True,
    }
    assert snapshot["real_success_evidence"]["feishu"]["id"] == "feishu_success"
    assert snapshot["real_success_evidence"]["github"]["operations"] == {
        "create_issue": True,
        "create_pr": True,
        "status": True,
        "sync": True,
    }
    assert "do-not-leak" not in json.dumps(snapshot)


def test_doctor_product_does_not_accept_partial_github_evidence(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "do-not-leak-deepseek")
    monkeypatch.setenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", "1")
    monkeypatch.setenv("FEISHU_ENABLE_WRITE", "1")

    store = AriadneStore(tmp_path)
    _seed_release_packet(tmp_path)
    store.save_execution_result(
        ExecutionResult(
            id="exec_codex_success",
            ticket_id="ticket_ari_003",
            backend_name="codex",
            dry_run=False,
            blocked=False,
            command="codex exec --cd /repo --prompt-file handoff.md",
            exit_code=0,
            changed_files=["demo_todo/cli.py"],
            test_command="pytest",
            test_exit_code=0,
        )
    )
    store.save_execution_result(
        ExecutionResult(
            id="exec_claude_success",
            ticket_id="ticket_ari_003",
            backend_name="claude-code",
            dry_run=False,
            blocked=False,
            command="claude --print < handoff.md",
            exit_code=0,
            changed_files=["tests/test_cli.py"],
            test_command="pytest",
            test_exit_code=0,
        )
    )
    store.save_feishu_write_result(
        FeishuWriteResult(
            id="feishu_success",
            ticket_id="ticket_ari_003",
            ticket_key="ARI-003",
            plan_id="feishu_plan",
            ok=True,
            blocked=False,
            dry_run=False,
            command="lark-cli docs create @content.md",
            returncode=0,
            document_id="doc_123",
            document_url="https://example.feishu.cn/docx/doc_123",
            operation_summary="Created Feishu doc.",
        )
    )
    _seed_llm_agent_product_evidence(store)
    store.save_github_integration_result(
        GitHubIntegrationResult(
            id="github_sync_only",
            ticket_id="ticket_ari_003",
            ticket_key="ARI-003",
            operation="sync",
            ok=True,
            blocked=False,
            repo="owner/repo",
            issue_number=42,
            issue_url="https://github.com/owner/repo/issues/42",
            comment_url="https://github.com/owner/repo/issues/42#issuecomment-1",
            branch="codex/product",
            commit_sha="abc123",
        )
    )

    monkeypatch.setattr(
        "ariadne_ltb.runtime.shutil.which",
        lambda command: {
            "codex": "/usr/local/bin/codex",
            "claude": "/usr/local/bin/claude",
            "lark-cli": "/usr/local/bin/lark-cli",
            "gh": "/usr/local/bin/gh",
        }.get(command),
    )
    monkeypatch.setattr("ariadne_ltb.doctor.shutil.which", lambda command: "/usr/local/bin/gh")
    monkeypatch.setattr(
        "ariadne_ltb.doctor.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "", ""),
    )
    monkeypatch.setattr(
        "ariadne_ltb.github_integration.shutil.which",
        lambda command: "/usr/local/bin/gh",
    )
    monkeypatch.setattr(
        "ariadne_ltb.github_integration.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "ok\n", ""),
    )

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "doctor", "product"])

    assert result.exit_code == 0, result.output
    snapshot = json.loads(
        (tmp_path / ".ariadne" / "doctor" / "product_readiness.json").read_text(encoding="utf-8")
    )
    statuses = {check["name"]: check["status"] for check in snapshot["checks"]}
    assert snapshot["production_acceptance_status"] == "action_required"
    assert statuses["real_github_write_evidence"] == "action_required"
    assert statuses["real_github_comment_evidence"] == "ready"
    assert statuses["real_github_issue_evidence"] == "action_required"
    assert statuses["real_github_pr_evidence"] == "action_required"
    assert statuses["real_github_status_evidence"] == "action_required"
    assert statuses["real_llm_agent_evidence"] == "ready"
    assert snapshot["real_success_evidence"]["github"] is None
    assert snapshot["real_failure_evidence"]["github"] is None


def test_doctor_product_separates_acceptance_from_unset_run_gates(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "do-not-leak-deepseek")
    monkeypatch.delenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", raising=False)
    monkeypatch.delenv("FEISHU_ENABLE_WRITE", raising=False)

    store = AriadneStore(tmp_path)
    _seed_release_packet(tmp_path)
    store.save_execution_result(
        ExecutionResult(
            id="exec_codex_success",
            ticket_id="ticket_ari_003",
            backend_name="codex",
            dry_run=False,
            blocked=False,
            command="codex exec --cd /repo --prompt-file handoff.md",
            exit_code=0,
            test_command="pytest",
            test_exit_code=0,
        )
    )
    store.save_execution_result(
        ExecutionResult(
            id="exec_claude_success",
            ticket_id="ticket_ari_003",
            backend_name="claude-code",
            dry_run=False,
            blocked=False,
            command="claude --print < handoff.md",
            exit_code=0,
            test_command="pytest",
            test_exit_code=0,
        )
    )
    store.save_feishu_write_result(
        FeishuWriteResult(
            id="feishu_success",
            ticket_id="ticket_ari_003",
            ticket_key="ARI-003",
            plan_id="feishu_plan",
            ok=True,
            blocked=False,
            dry_run=False,
            command="lark-cli docs create @content.md",
            returncode=0,
            document_id="doc_123",
            document_url="https://example.feishu.cn/docx/doc_123",
            operation_summary="Created Feishu doc.",
        )
    )
    _seed_llm_agent_product_evidence(store)
    _seed_full_github_product_evidence(store)

    def fake_which(command: str) -> str | None:
        return {
            "codex": "/usr/local/bin/codex",
            "claude": "/usr/local/bin/claude",
            "lark-cli": "/usr/local/bin/lark-cli",
            "gh": "/usr/local/bin/gh",
        }.get(command)

    def fake_github_run(command, **kwargs):  # type: ignore[no-untyped-def]
        if command[:3] == ["gh", "auth", "status"]:
            return subprocess.CompletedProcess(command, 0, "", "")
        if command[:3] == ["git", "config", "--get"] and command[-1] == "remote.origin.url":
            return subprocess.CompletedProcess(command, 0, "https://github.com/owner/repo.git\n", "")
        if command[:3] == ["git", "config", "--get"]:
            return subprocess.CompletedProcess(command, 1, "", "")
        if command[:2] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(command, 0, "codex/product\n", "")
        if command[:3] == ["git", "ls-remote", "--heads"]:
            return subprocess.CompletedProcess(command, 0, "abc123\trefs/heads/codex/product\n", "")
        return subprocess.CompletedProcess(command, 1, "", f"unexpected command: {command}")

    monkeypatch.setattr("ariadne_ltb.runtime.shutil.which", fake_which)
    monkeypatch.setattr("ariadne_ltb.doctor.shutil.which", fake_which)
    monkeypatch.setattr("ariadne_ltb.github_integration.shutil.which", fake_which)
    monkeypatch.setattr(
        "ariadne_ltb.doctor.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "", ""),
    )
    monkeypatch.setattr("ariadne_ltb.github_integration.subprocess.run", fake_github_run)

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "doctor", "product"])

    assert result.exit_code == 0, result.output
    assert "Product readiness: action_required" in result.output
    assert "Production acceptance: ready" in result.output
    assert "Run gates: action_required" in result.output
    snapshot = json.loads(
        (tmp_path / ".ariadne" / "doctor" / "product_readiness.json").read_text(encoding="utf-8")
    )
    assert snapshot["overall_status"] == "action_required"
    assert snapshot["production_acceptance_status"] == "ready"
    assert snapshot["run_gate_status"] == "action_required"

    acceptance_required = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "doctor", "product", "--require-acceptance-ready"],
    )
    assert acceptance_required.exit_code == 0, acceptance_required.output
    assert "Production acceptance: ready" in acceptance_required.output

    gates_required = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "doctor", "product", "--require-run-gates-ready"],
    )
    assert gates_required.exit_code == 2, gates_required.output
    assert "requirement failed: run gates are action_required, expected ready" in gates_required.output


def test_gitignore_contains_v1_secret_patterns() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    for pattern in [".env", ".env.*", "*.secret", ".secrets", "secrets/", ".ariadne/"]:
        assert pattern in gitignore


def test_verify_v1_script_exists_and_is_executable() -> None:
    script = ROOT / "scripts" / "verify_v1.sh"
    text = script.read_text(encoding="utf-8")
    assert script.exists()
    assert text.startswith("#!/usr/bin/env bash")
    assert "doctor product --require-acceptance-ready" in text
    assert "Deterministic regression loop only" in text
