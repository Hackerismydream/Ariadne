from __future__ import annotations

import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.evidence import generate_release_evidence_packet
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import ExecutionResult, FeishuWriteResult
from ariadne_ltb.orchestrator import TicketRunOrchestrator
from ariadne_ltb.storage import AriadneStore
from test_v1_doctor_release import (
    _seed_full_github_product_evidence,
    _seed_llm_agent_product_evidence,
    _seed_ready_landing_gate_evidence,
    _seed_release_packet,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_release_evidence_packet_records_current_store_and_board(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex")

    packet, path = generate_release_evidence_packet(store)

    assert path.exists()
    assert packet.ticket_count >= 4
    assert packet.execution_result_count >= 1
    assert packet.review_report_count >= 1
    assert packet.board_path
    assert Path(packet.board_path).exists()
    assert packet.store_invariants_ok is True
    assert "board" in packet.evidence_refs
    assert "integration_doctor" in packet.evidence_refs
    assert "runtime_capabilities" in packet.evidence_refs
    assert "backend_smoke_evidence" in packet.evidence_refs
    assert "feishu_integrations" in packet.evidence_refs
    assert "github_integrations" in packet.evidence_refs
    assert "landing_gate_reports" in packet.evidence_refs
    assert "product_readiness" in packet.evidence_refs
    assert Path(packet.evidence_refs["integration_doctor"]).exists()
    assert Path(packet.evidence_refs["runtime_capabilities"]).exists()
    assert Path(packet.evidence_refs["product_readiness"]).exists()
    assert packet.product_readiness_status in {"ready", "action_required", "blocked"}
    assert packet.production_acceptance_status in {"ready", "action_required", "blocked"}
    assert packet.run_gate_status in {"ready", "action_required", "blocked"}
    assert "real_codex_execution_evidence" in packet.product_readiness_checks
    assert "real_llm_agent_evidence" in packet.product_readiness_checks
    assert "real_feishu_write_evidence" in packet.product_readiness_checks
    assert "landing_gate_evidence" in packet.product_readiness_checks
    assert "llm_agents" in packet.real_success_evidence
    assert "codex" in packet.real_success_evidence
    assert "github" in packet.real_failure_evidence
    assert "landing_gate" in packet.local_failure_evidence
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["id"] == packet.id
    assert persisted["evidence_refs"]["integration_doctor"].endswith("integrations.json")
    assert persisted["evidence_refs"]["product_readiness"].endswith("product_readiness.json")
    assert persisted["evidence_refs"]["backend_smoke_evidence"].endswith("backend_smoke")
    assert persisted["evidence_refs"]["landing_gate_reports"].endswith("artifact_index")
    assert persisted["production_acceptance_status"] in {"ready", "action_required", "blocked"}
    assert persisted["run_gate_status"] in {"ready", "action_required", "blocked"}
    assert "real_github_write_evidence" in persisted["product_readiness_checks"]
    assert "real_llm_agent_evidence" in persisted["product_readiness_checks"]
    assert "landing_gate_evidence" in persisted["product_readiness_checks"]


def test_evidence_packet_cli_writes_machine_readable_json(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex")

    result = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "evidence", "packet", "--output", "json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ticket_count"] >= 4
    assert payload["execution_result_count"] >= 1
    assert payload["review_report_count"] >= 1
    assert "integration_doctor" in payload["evidence_refs"]
    assert "product_readiness" in payload["evidence_refs"]
    assert payload["production_acceptance_status"] in {"ready", "action_required", "blocked"}
    assert payload["run_gate_status"] in {"ready", "action_required", "blocked"}
    assert "real_codex_execution_evidence" in payload["product_readiness_checks"]
    assert "real_llm_agent_evidence" in payload["product_readiness_checks"]
    assert "landing_gate_evidence" in payload["product_readiness_checks"]
    assert (tmp_path / ".ariadne" / "doctor" / "integrations.json").exists()
    assert (tmp_path / ".ariadne" / "doctor" / "product_readiness.json").exists()
    assert (tmp_path / ".ariadne" / "evidence" / "release_evidence_packet.json").exists()


def test_evidence_packet_require_acceptance_ready_blocks_fake_only_store(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex")

    result = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "evidence", "packet", "--require-acceptance-ready"],
    )

    assert result.exit_code == 2, result.output
    assert "production acceptance: blocked" in result.output
    assert "requirement failed: production acceptance is blocked, expected ready" in result.output
    assert (tmp_path / ".ariadne" / "evidence" / "release_evidence_packet.json").exists()


def test_evidence_packet_requirement_flags_separate_acceptance_and_run_gates(
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
    _seed_ready_landing_gate_evidence(store)

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

    acceptance_required = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "evidence", "packet", "--require-acceptance-ready"],
    )
    assert acceptance_required.exit_code == 0, acceptance_required.output
    assert "production acceptance: ready" in acceptance_required.output
    assert "run gates: action_required" in acceptance_required.output

    gates_required = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "evidence", "packet", "--require-run-gates-ready"],
    )
    assert gates_required.exit_code == 2, gates_required.output
    assert "production acceptance: ready" in gates_required.output
    assert "requirement failed: run gates are action_required, expected ready" in (
        gates_required.output
    )
