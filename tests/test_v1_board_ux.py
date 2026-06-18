from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.board_server import board_serve_command
from ariadne_ltb.cli import app
from ariadne_ltb.inbox import refresh_inbox
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import (
    ArtifactType,
    BackendSmokeEvidence,
    FeishuWriteResult,
    FailureReason,
    GitHubIntegrationResult,
    ReleaseEvidencePacket,
)
from ariadne_ltb.orchestrator import TicketRunOrchestrator
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_board_contains_v1_workbench_sections(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex")
    gate = CliRunner().invoke(app, ["--root", str(tmp_path), "landing", "gate", "ARI-003"])
    assert gate.exit_code == 0, gate.output

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "export", "board"])
    board = (tmp_path / ".ariadne" / "board" / "index.md").read_text(encoding="utf-8")

    assert result.exit_code == 0, result.output
    for heading in [
        "Ariadne v1.0 Workbench",
        "System Summary",
        "Agent Queue",
        "Tickets by Status",
        "Active Assignments",
        "Daemon / Runtime",
        "Agent Comments",
        "Recent Journal Events",
        "Executed Tickets",
        "Next Tickets",
        "Backend Capability",
        "Safety Gates",
        "Assignment Retry Chain",
        "Agent Handoffs",
        "Codex Gate Status",
        "Execution Permission Profile",
        "Provider Audit Artifacts",
        "Landing Evidence",
        "Landing Gate",
    ]:
        assert heading in board
    assert "landing_evidence.json" in board
    assert "- Partial: `false`" in board
    assert "landing_gate_report.json" in board
    assert "- Status: `ready`" in board
    assert "`landing_gate_evaluated`" in board


def test_board_shows_inbox_repair_ticket_evidence(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    store.save_assignment(assignment.mark_failed("provider config invalid", FailureReason.PROVIDER_CONFIG_INVALID))
    item = refresh_inbox(store)[0]

    repair = CliRunner().invoke(app, ["--root", str(tmp_path), "inbox", "create-ticket", item.id])
    assert repair.exit_code == 0, repair.output

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "export", "board"])
    board = (tmp_path / ".ariadne" / "board" / "index.md").read_text(encoding="utf-8")

    assert result.exit_code == 0, result.output
    assert "## Inbox" in board
    assert f"- `{item.id}` status=`acknowledged` severity=`high`" in board
    assert "failure=`provider_config_invalid`" in board
    assert "action=`fix_provider_configuration`" in board
    assert "repair=`ARI-" in board
    assert f"- Evidence: `{item.evidence_ref}`" in board
    assert "- Resolution: repair ticket created:" in board


def test_board_shows_github_status_evidence(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    store.save_github_integration_result(
        GitHubIntegrationResult(
            id="github_link",
            ticket_id=ticket.id,
            ticket_key=ticket.key,
            operation="link",
            ok=True,
            repo="Hackerismydream/Ariadne",
            issue_number=8,
            issue_url="https://github.com/Hackerismydream/Ariadne/issues/8",
        )
    )
    store.save_github_integration_result(
        GitHubIntegrationResult(
            id="github_status",
            ticket_id=ticket.id,
            ticket_key=ticket.key,
            operation="status",
            ok=True,
            repo="Hackerismydream/Ariadne",
            issue_number=8,
            issue_url="https://github.com/Hackerismydream/Ariadne/issues/8",
            pr_number=9,
            pr_url="https://github.com/Hackerismydream/Ariadne/pull/9",
            branch="codex/ariadne-production-frontend-integration",
            commit_sha="abc123",
            evidence={
                "issue": {"number": 8, "state": "OPEN"},
                "pr": {
                    "number": 9,
                    "state": "OPEN",
                    "baseRefName": "main",
                    "headRefName": "codex/ariadne-production-frontend-integration",
                    "mergeable": "MERGEABLE",
                    "reviewDecision": "",
                },
                "checks": [],
                "checks_status": "no_checks_reported",
            },
        )
    )

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "export", "board"])
    board = (tmp_path / ".ariadne" / "board" / "index.md").read_text(encoding="utf-8")

    assert result.exit_code == 0, result.output
    assert "### GitHub Integration" in board
    assert "- PR: `#9`" in board
    assert "- PR base: `main`" in board
    assert "- Mergeable: `MERGEABLE`" in board
    assert "- Review decision: `none`" in board
    assert "- Checks status: `no_checks_reported`" in board
    assert "- Checks summary: pass=`0` pending=`0` fail=`0` total=`0`" in board
    assert "- Recent GitHub operations:" in board


def test_board_shows_production_acceptance_evidence(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, [SOURCE_FIXTURES[2]])
    store.save_release_evidence_packet(
        ReleaseEvidencePacket(
            id="release_evidence_board",
            root_path=str(tmp_path),
            product_readiness_status="action_required",
            production_acceptance_status="ready",
            run_gate_status="action_required",
            product_readiness_checks={
                "landing_gate_evidence": "ready",
                "real_codex_execution_evidence": "ready",
                "real_claude_execution_evidence": "ready",
                "real_feishu_write_evidence": "ready",
            },
            local_success_evidence={
                "landing_gate": {
                    "id": "landing_gate_board",
                    "status": "ready",
                    "ticket_key": "ARI-003",
                    "path": ".ariadne/artifacts/ticket_ari_003/landing_gate_report.json",
                },
            },
            real_success_evidence={
                "codex": {
                    "id": "backend_smoke_codex",
                    "source": "backend_smoke",
                    "ticket_key": "ARI-003",
                    "execution_result_id": "execution_codex",
                },
                "github": {
                    "operations": {
                        "create_issue": True,
                        "create_pr": True,
                        "sync": True,
                        "status": True,
                    },
                    "issue_url": "https://github.com/Hackerismydream/Ariadne/issues/8",
                    "pr_url": "https://github.com/Hackerismydream/Ariadne/pull/9",
                },
            },
        )
    )

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "export", "board"])
    board = (tmp_path / ".ariadne" / "board" / "index.md").read_text(encoding="utf-8")

    assert result.exit_code == 0, result.output
    assert "## Production Acceptance Evidence" in board
    assert "- Production acceptance: `ready`" in board
    assert "| `landing_gate_evidence` | `ready` |  |" in board
    assert "| `real_codex_execution_evidence` | `ready` |  |" in board
    assert "### Local Gate Evidence" in board
    assert "`landing_gate`: id=`landing_gate_board`; status=`ready`; ticket_key=`ARI-003`" in board
    assert "`codex`: id=`backend_smoke_codex`; source=`backend_smoke`; ticket_key=`ARI-003`" in board
    assert "`github`: issue_url=`https://github.com/Hackerismydream/Ariadne/issues/8`" in board


def test_board_counts_completed_failed_github_checks_as_failures(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    store.save_github_integration_result(
        GitHubIntegrationResult(
            id="github_status_with_checks",
            ticket_id=ticket.id,
            ticket_key=ticket.key,
            operation="status",
            ok=True,
            repo="Hackerismydream/Ariadne",
            pr_number=9,
            evidence={
                "pr": {"number": 9, "state": "OPEN", "baseRefName": "main"},
                "checks": [
                    {"name": "unit", "bucket": "pass"},
                    {"name": "lint", "state": "queued"},
                    {"name": "integration", "state": "completed", "conclusion": "failure"},
                ],
                "checks_status": "captured",
            },
        )
    )

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "export", "board"])
    board = (tmp_path / ".ariadne" / "board" / "index.md").read_text(encoding="utf-8")

    assert result.exit_code == 0, result.output
    assert "- Checks summary: pass=`1` pending=`1` fail=`1` total=`3`" in board


def test_board_export_tolerates_legacy_unknown_artifact_types(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    ticket = store.resolve_ticket("ARI-003")
    artifact_id = "artifact_legacy_landing_gate"
    (store.artifact_index_dir / f"{artifact_id}.json").write_text(
        json.dumps(
            {
                "id": artifact_id,
                "ticket_id": ticket.id,
                "agent_run_id": "legacy",
                "artifact_type": "landing_gate",
                "path": str(tmp_path / ".ariadne" / "legacy.json"),
                "summary": "Legacy landing gate artifact.",
                "created_at": "2026-06-17T00:00:00Z",
                "metadata": {},
            }
        ),
        encoding="utf-8",
    )
    store.save_ticket(ticket.model_copy(update={"artifact_ids": [artifact_id]}))

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "export", "board"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / ".ariadne" / "board" / "index.md").exists()


def test_board_serve_command_builds_expected_handler(tmp_path: Path) -> None:
    board_dir = tmp_path / ".ariadne" / "board"
    board_dir.mkdir(parents=True)
    (board_dir / "index.html").write_text("<h1>Ariadne</h1>", encoding="utf-8")

    config = board_serve_command(board_dir, port=0, dry_run=True)

    assert config["directory"] == str(board_dir.resolve())
    assert config["port"] == 0


def test_cli_outputs_readable_ticket_state(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    tickets = ingest_sources(store, SOURCE_FIXTURES)
    ticket = next(ticket for ticket in tickets if ticket.key == "ARI-003")
    store.save_backend_smoke_evidence(
        BackendSmokeEvidence(
            id="backend_smoke_ticket_show",
            backend_name="codex",
            ticket_id=ticket.id,
            ticket_key=ticket.key,
            assignment_id="assignment_ticket_show",
            assignment_status="done",
            succeeded=True,
            execution_result_id="execution_ticket_show",
            exit_code=0,
            test_exit_code=0,
            review_verdict="pass",
        )
    )
    store.write_artifact(
        ticket.id,
        "run_llm_ticket_show",
        ArtifactType.LLM_AGENT_RESULT,
        "llm_build_lead.json",
        "{}\n",
        "DeepSeek LLM build lead result",
        metadata={
            "llm_role": "build_lead",
            "provider": "deepseek",
            "model": "deepseek-v4-pro",
            "succeeded": True,
        },
    )
    store.save_feishu_write_result(
        FeishuWriteResult(
            id="feishu_ticket_show",
            ticket_id=ticket.id,
            ticket_key=ticket.key,
            plan_id="feishu_plan_ticket_show",
            ok=True,
            document_url="https://example.feishu.cn/docx/ticket-show",
            operation_summary="created doc",
        )
    )
    store.save_github_integration_result(
        GitHubIntegrationResult(
            id="github_ticket_show",
            ticket_id=ticket.id,
            ticket_key=ticket.key,
            operation="status",
            ok=True,
            repo="Hackerismydream/Ariadne",
            issue_number=8,
            issue_url="https://github.com/Hackerismydream/Ariadne/issues/8",
            pr_number=9,
            pr_url="https://github.com/Hackerismydream/Ariadne/pull/9",
            comment_url="https://github.com/Hackerismydream/Ariadne/issues/8#issuecomment-1",
        )
    )
    store.save_release_evidence_packet(
        ReleaseEvidencePacket(
            id="release_evidence_ticket_show",
            root_path=str(tmp_path),
            product_readiness_status="action_required",
            production_acceptance_status="ready",
        )
    )
    runner = CliRunner()
    assign = runner.invoke(app, ["--root", str(tmp_path), "ticket", "assign", "ARI-003", "--to", "fake-codex"])
    show = runner.invoke(app, ["--root", str(tmp_path), "ticket", "show", "ARI-003"])

    assert assign.exit_code == 0, assign.output
    assert show.exit_code == 0, show.output
    assert "Assignment:" in show.output
    assert "Status:" in show.output
    assert "Production Evidence:" in show.output
    assert "Backend smoke:" in show.output
    assert "codex: pass execution=execution_ticket_show" in show.output
    assert "LLM agents:" in show.output
    assert "build_lead: pass provider=deepseek model=deepseek-v4-pro" in show.output
    assert "Feishu: pass doc=https://example.feishu.cn/docx/ticket-show" in show.output
    assert "GitHub: ops=status issue=https://github.com/Hackerismydream/Ariadne/issues/8" in show.output
    assert "Release packet: production_acceptance=ready" in show.output
