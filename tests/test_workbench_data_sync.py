from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import (
    ArtifactType,
    BacklogOperation,
    BacklogOperationType,
    BacklogPreview,
    BacklogUpdateTrigger,
    BuildTicket,
    FeishuWriteResult,
    FailureReason,
    InboxItem,
    InboxSeverity,
    InboxStatus,
    ReleaseEvidencePacket,
    TicketStatus,
)
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))
SYNC_SCRIPT = ROOT / "frontend" / "ariadne-workbench" / "scripts" / "sync-local-data.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required for workbench data sync")
def test_workbench_data_sync_includes_ticket_production_evidence(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = next(ticket for ticket in ingest_sources(store, SOURCE_FIXTURES) if ticket.key == "ARI-003")
    store.write_artifact(
        ticket.id,
        "run_llm_sync",
        ArtifactType.LLM_AGENT_RESULT,
        "llm_build_lead.json",
        json.dumps(
            {
                "role": "build_lead",
                "succeeded": True,
                "provider": "deepseek",
                "model": "deepseek-v4-pro",
                "usage": {"total_tokens": 123},
                "output_json": {"summary": "Build lead accepted the ticket.", "decision": "verify"},
            }
        ),
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
            id="feishu_sync",
            ticket_id=ticket.id,
            ticket_key=ticket.key,
            plan_id="feishu_plan_sync",
            ok=True,
            dry_run=False,
            document_url="https://example.feishu.cn/docx/sync",
            operation_summary="created doc",
        )
    )
    store.save_release_evidence_packet(
        ReleaseEvidencePacket(
            id="release_evidence_sync",
            root_path=str(tmp_path),
            ticket_count=4,
            execution_result_count=12,
            review_report_count=7,
            inbox_item_count=2,
            product_readiness_status="action_required",
            production_acceptance_status="ready",
            run_gate_status="action_required",
            product_readiness_checks={
                "real_llm_agent_evidence": "ready",
                "real_codex_execution_evidence": "ready",
                "external_execution_gate": "action_required",
            },
            readiness_next_actions=[
                "Set ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 only when running a confirmed Codex/Claude task.",
            ],
            readiness_blockers=[
                {
                    "name": "external_execution_gate",
                    "status": "action_required",
                    "summary": "External execution gate is unset.",
                    "next_action": "Set ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 only when running a confirmed Codex/Claude task.",
                }
            ],
            evidence_packet_stale=True,
            evidence_packet_stale_reasons=["ticket_count changed from 3 to 4"],
            real_success_evidence={
                "llm_agents": {"id": "llm_sync"},
                "codex": {"id": "codex_sync"},
            },
            real_failure_evidence={
                "github": {"id": "github_blocked"},
            },
            evidence_refs={
                "product_readiness": ".ariadne/doctor/product_readiness.json",
            },
        )
    )
    store.save_backlog_preview(
        BacklogPreview(
            id="backlog_preview_sync",
            trigger_type=BacklogUpdateTrigger.MEMORY_GAP,
            trigger_ref="memory_record_sync",
            idempotency_key="backlog_preview_sync_key",
            base_ticket_fingerprint="fingerprint_sync",
            applied_update_id="backlog_update_sync",
            applied_at="2026-06-18T00:00:00Z",
            operations=[
                BacklogOperation(
                    id="operation_sync",
                    operation_type=BacklogOperationType.ADD_TICKET,
                    reason="Memory records are written but not searchable.",
                    ticket_key="ARI-999",
                    title="Index memory records",
                    priority="high",
                    metadata={"suggestion": {"suggested_build_decision": "code_task"}},
                )
            ],
            rationale="Previewed memory-gap backlog changes for ARI-003.",
            evidence_refs=[ticket.id, "memory_record_sync"],
            created_at="2026-06-18T00:00:00Z",
        )
    )
    store.save_inbox_items(
        [
            InboxItem(
                id="inbox_sync",
                source_type="agent_run",
                source_id="run_sync",
                ticket_id=ticket.id,
                ticket_key=ticket.key,
                title="ARI-003 LLM agent blocked",
                summary="schema validation failed",
                severity=InboxSeverity.HIGH,
                status=InboxStatus.ACKNOWLEDGED,
                failure_reason=FailureReason.AGENT_ERROR,
                evidence_ref=".ariadne/artifacts/ticket/llm_knowledge.json",
                recommended_action="human_review_required",
                resolution_note="repair ticket created: ARI-998",
            )
        ]
    )
    store.save_ticket(
        BuildTicket(
            id="ticket_repair_sync",
            key="ARI-998",
            title="Repair ARI-003 agent run",
            description="Repair inbox item.",
            source_type="inbox_recovery",
            source_ref=".ariadne/inbox/items.json",
            status=TicketStatus.PLANNING,
            metadata={"generated_from_inbox_item_id": "inbox_sync"},
        )
    )

    output_path = tmp_path / "workbench.json"
    subprocess.run(
        ["node", str(SYNC_SCRIPT)],
        check=True,
        cwd=ROOT / "frontend" / "ariadne-workbench",
        env={
            **os.environ,
            "ARIADNE_WORKBENCH_ARIADNE_ROOT": str(tmp_path / ".ariadne"),
            "ARIADNE_WORKBENCH_OUTPUT_PATH": str(output_path),
        },
    )
    data = json.loads(output_path.read_text(encoding="utf-8"))
    synced_ticket = next(item for item in data["tickets"] if item["key"] == "ARI-003")

    assert synced_ticket["llmAgents"][0]["role"] == "build_lead"
    assert synced_ticket["llmAgents"][0]["provider"] == "deepseek"
    assert synced_ticket["llmAgents"][0]["totalTokens"] == 123
    assert synced_ticket["feishu"]["documentUrl"] == "https://example.feishu.cn/docx/sync"
    assert synced_ticket["releaseEvidence"]["productionAcceptanceStatus"] == "ready"
    assert data["backlogMutationPreview"]["status"] == "applied"
    assert data["backlogMutationPreview"]["previewId"] == "backlog_preview_sync"
    assert data["backlogMutationPreview"]["triggerType"] == "memory_gap"
    assert data["backlogMutationPreview"]["added"] == 1
    assert data["backlogChanges"][0]["previewId"] == "backlog_preview_sync"
    assert data["backlogChanges"][0]["triggerType"] == "memory_gap"
    assert data["backlogChanges"][0]["operationType"] == "add_ticket"
    assert data["backlogChanges"][0]["ticketKey"] == "ARI-999"
    assert data["releaseEvidence"]["id"] == "release_evidence_sync"
    assert data["releaseEvidence"]["ticketCount"] == 4
    assert data["releaseEvidence"]["executionResultCount"] == 12
    assert data["releaseEvidence"]["productReadinessChecks"]["real_llm_agent_evidence"] == "ready"
    assert data["releaseEvidence"]["productReadinessChecks"]["external_execution_gate"] == "action_required"
    assert data["releaseEvidence"]["readinessNextActions"][0].startswith("Set ARIADNE_ENABLE")
    assert data["releaseEvidence"]["readinessBlockers"][0]["name"] == "external_execution_gate"
    assert data["releaseEvidence"]["evidencePacketStale"] is True
    assert data["releaseEvidence"]["evidencePacketStaleReasons"][0] == "ticket_count changed from 3 to 4"
    assert data["releaseEvidence"]["realSuccessEvidence"]["codex"]["id"] == "codex_sync"
    assert data["releaseEvidence"]["realFailureEvidence"]["github"]["id"] == "github_blocked"
    assert data["releaseEvidence"]["evidenceRefs"]["product_readiness"].endswith("product_readiness.json")
    synced_inbox = next(item for item in data["inbox"] if item["id"] == "inbox_sync")
    assert synced_inbox["status"] == "acknowledged"
    assert synced_inbox["severity"] == "high"
    assert synced_inbox["sourceType"] == "agent_run"
    assert synced_inbox["sourceId"] == "run_sync"
    assert synced_inbox["ticketKey"] == "ARI-003"
    assert synced_inbox["kind"] == "blocker"
    assert synced_inbox["failureReason"] == "agent_error"
    assert synced_inbox["recommendedAction"] == "human_review_required"
    assert synced_inbox["evidenceRef"].endswith("llm_knowledge.json")
    assert synced_inbox["resolutionNote"] == "repair ticket created: ARI-998"
    assert synced_inbox["repairTicketId"] == "ticket_repair_sync"
    assert synced_inbox["repairTicketKey"] == "ARI-998"
